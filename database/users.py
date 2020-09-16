import datetime
from collections import defaultdict
from .promo_db import get_connection


push_timedelta = datetime.timedelta(minutes=15)


def get_tables(is_ios: bool) -> (str, str):
    """returns (users_table, links_table)"""
    if is_ios:
        return ("ios_users", "ios_shops_users")
    else:
        return ("android_users", "android_shops_users")


def _insert_user(token: str, is_user_active: bool, is_ios: bool, cur):
    if is_ios and len(token) != 64:
        return

    table, _ = get_tables(is_ios)

    query = f"""INSERT INTO {table}
                (token, last_push_time, last_visit_time, is_active)
                VALUES (%s, NOW(), NOW(), %s); """
    args = (token, int(is_user_active))
    cur.execute(query, args)


def insert_user_info(token: str,
                     new_shops_user_liked: list,
                     is_user_active: bool,
                     is_ios: bool,
                     **kwargs):
    if not token:
        return

    # user_ip = kwargs.get('user_ip', '')

    new_shops_user_liked = frozenset(new_shops_user_liked)

    users_table, links_table = get_tables(is_ios)

    conn = get_connection()

    with conn:
        cur = conn.cursor()
        with cur:
            if (user_id := get_user_id(token, users_table, cur)):
                _update_user_info(user_id, is_user_active, users_table, cur)
                old_shops_user_liked: frozenset = \
                    _get_favorite_shops(user_id,
                                        links_table,
                                        cur)
            else:
                _insert_user(token, is_user_active, is_ios, cur)
                user_id = get_user_id(token, users_table, cur)
                old_shops_user_liked = frozenset()

            if not user_id:
                raise(IndexError("error while inserting new user"
                                 "in insert_shops_user_liked"))

            shops_to_delete = old_shops_user_liked - new_shops_user_liked
            shops_to_insert = new_shops_user_liked - old_shops_user_liked

            shops_to_delete_indices: list = \
                get_shops_indices(shops_to_delete, cur)

            shops_to_insert_indices: list = \
                get_shops_indices(shops_to_insert, cur)

            if len(shops_to_insert_indices) != len(shops_to_insert) or \
                    len(shops_to_delete_indices) != len(shops_to_delete):

                raise IndexError(f"some shop is not in db;\n"
                                 f"{shops_to_delete}\n"
                                 f"{shops_to_insert}")

            if shops_to_delete_indices:
                _delete_liked_shops_for_user(user_id,
                                             shops_to_delete_indices,
                                             links_table,
                                             cur)

            if shops_to_insert_indices:
                _insert_liked_shops_for_user(user_id,
                                             shops_to_insert_indices,
                                             links_table,
                                             cur)


def get_user_id(token: str, table: str, cur) -> int:
    cur.execute(f"SELECT id FROM {table} WHERE token = %s LIMIT 1;",
                (token,))
    if (id := cur.fetchone()):
        return id[0]
    else:
        return 0


def _get_favorite_shops(user_id: int, links_table: str, cur) -> frozenset:
    query = f"""SELECT shop FROM shops
                WHERE id IN (
                    SELECT shop_id FROM {links_table}
                    WHERE user_id = %s
                );
            """
    args = (user_id,)
    cur.execute(query, args)

    shops_indices = cur.fetchall()

    if not shops_indices:
        return frozenset()

    shops_indices = frozenset(map(lambda s: s[0], shops_indices))

    return shops_indices


def get_shops_indices(shops_names: set, cur) -> list:
    if not shops_names:
        return []
    cur.execute("SELECT id FROM shops WHERE shop IN %s; ", (shops_names,))
    return cur.fetchall()


def _update_user_info(user_id: int,
                      is_user_active: bool,
                      users_table: str,
                      cur):

    is_user_active = int(is_user_active)  # NOTE: can be only 1 or 0

    query = f"""UPDATE {users_table}
                SET is_active = %s, last_visit_time = NOW()
                WHERE id = %s; """
    args = (is_user_active, user_id,)
    cur.execute(query, args)


def _delete_liked_shops_for_user(user_id: int,
                                 shops_indices: list,
                                 links_table: str,
                                 cur):
    """deletes links on shops from links table for current user"""

    if not user_id or not shops_indices:
        return

    query = f"""DELETE FROM {links_table}
                WHERE user_id = %s
                AND shop_id IN %s; """
    args = (user_id, shops_indices,)
    cur.execute(query, args)


def _insert_liked_shops_for_user(user_id: int,
                                 shops_indices: set,
                                 links_table: str,
                                 cur):
    """links user with shops in links table"""

    if not shops_indices:
        return

    for shop_id in shops_indices:
        query = f"""INSERT INTO {links_table}
                    (shop_id, user_id)
                    VALUES (%s, %s); """
        args = (shop_id, user_id,)
        cur.execute(query, args)


def get_tokens_linked_with_shops(shops_indices: list,
                                 users_table: str,
                                 links_table: str) -> list:
    """
        returns dict in format str: list[str]
    example:
        {"token1": ["shop1", "shop2"]}
    every key-value contains token and list of shops names
    """

    if not shops_indices:
        raise IndexError(f"not found shop indices"
                         f"for indices: {shops_indices}")

    token_shops_dict = defaultdict(list)

    now = datetime.datetime.now()

    conn = get_connection()

    with conn:
        cur = conn.cursor()
        with cur:
            query = """SELECT id, shop FROM shops
                       WHERE id IN %s;"""
            args = (shops_indices,)
            cur.execute(query, args)

            for shop_id, current_shop in cur.fetchall():
                query = f"""SELECT id, token, last_push_time
                            FROM {users_table}
                            WHERE id IN (
                                SELECT user_id FROM {links_table}
                                WHERE shop_id = %s
                            )
                            AND is_active = 1; """
                args = (shop_id,)
                cur.execute(query, args)

                tokens_that_like_current_shop = cur.fetchall()

                if not tokens_that_like_current_shop:
                    continue

                cur.execute(f"""UPDATE {users_table}
                                SET last_push_time = NOW()
                                WHERE id IN %s; """,
                            (list(map(lambda i: i[0],
                                      tokens_that_like_current_shop)),))

                for id, token, last_push_time in tokens_that_like_current_shop:
                    if now - last_push_time > push_timedelta:
                        token_shops_dict[token].append(current_shop)

    return token_shops_dict


def get_all_tokens() -> (list, list):
    """
        Returns ios, android
    needed for sending msg from admin
    """
    conn = get_connection()

    with conn:
        cur = conn.cursor()
        with cur:
            cur.execute("""SELECT token
                           FROM ios_users
                           WHERE is_active = 1; """)
            ios_tokens = list(map(lambda t: t[0], cur.fetchall()))

            cur.execute("""SELECT token
                           FROM android_users
                           WHERE is_active = 1; """)
            android_tokens = list(map(lambda t: t[0], cur.fetchall()))

    return ios_tokens, android_tokens


def delete_tokens(tokens: list, is_ios: bool) -> int:
    """needed only when making request to apns with invalid tokens
        Returns:
            int number that matches counter of deleted tokens
    """
    if not tokens:
        return 0

    users_table, _ = get_tables(is_ios)

    conn = get_connection()

    with conn:
        cur = conn.cursor()
        with cur:
            query = f"DELETE FROM {users_table} WHERE token IN %s; "
            args = (tokens,)
            return cur.execute(query, args)


if __name__ == '__main__':
    pass
