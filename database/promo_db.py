import json
from . import knn_img_color
import constants
import data_classes
from datetime import datetime
from os import listdir
from os.path import exists
from random import randint
from .utils import get_connection, any_is_empty
from re import sub, DOTALL


def get_photos_links(photos_directory: str) -> (str, str):
    """can ret ('', '')
       first: preview, second: background
       returns links for json db"""

    background_img_link = ""
    preview_img_link = ""

    local_img_dir = f"{constants.images_dir_path}/{photos_directory}"

    if exists(local_img_dir):
        for file in listdir(local_img_dir):
            if file.startswith("back"):  # background img
                background_img_link = \
                    f"{constants.server_addr}/{photos_directory}/{file}"

            elif file.startswith("prev"):
                preview_img_link = \
                    f"{constants.server_addr}/{photos_directory}/{file}"

    return preview_img_link, background_img_link


def _get_android_json(db: list) -> str:

    unix_timestamp = datetime(1970, 1, 1)

    for category in db:
        for shop in category.shops:
            for promocode in shop.promoCodes:
                promocode.estimatedDate = float(
                    (promocode.estimatedDate - unix_timestamp)
                    .total_seconds() * 1000
                )
                promocode.addingDate = float(
                    (promocode.addingDate - unix_timestamp)
                    .total_seconds() * 1000
                )

    return json.dumps(db,
                      default=lambda obj: obj.__dict__,
                      ensure_ascii=False,
                      check_circular=True,
                      allow_nan=False,
                      indent=1)


def _get_ios_json(db: list) -> str:

    db = _change_data_for_ios(db)

    return json.dumps(db,
                      default=lambda obj: obj.__dict__,
                      ensure_ascii=False,
                      check_circular=True,
                      allow_nan=False,
                      indent=1)


def _change_data_for_ios(categories: list):
    unix_timestamp = datetime(1970, 1, 1)
    swift_timestamp = datetime(2001, 1, 1)
    swift_unix_delta = \
        float((swift_timestamp - unix_timestamp).total_seconds())

    for category in categories:
        for shop in category.shops:
            shop.placeholderColor = \
                _convert_hex_to_rgba(shop.placeholderColor)

            for promocode in shop.promoCodes:
                promocode.estimatedDate = \
                    (promocode.estimatedDate / 1000) - swift_unix_delta

                promocode.addingDate = \
                    (promocode.addingDate / 1000) - swift_unix_delta

    return categories


def read_all_db() -> list:
    """returns list of nested classes;
        list of categories -> categories -> shops -> promocodes
    """

    conn = get_connection()

    with conn:
        cur = conn.cursor()
        cur.execute("""DELETE FROM promocodes
                       WHERE DATE(expiration_date) < CURDATE(); """)

        shopCategoriesList = list()

        hot_shops_names = _get_hot_shop_names(cur)

        cur.execute("""SELECT id, category, priority
                       FROM categories
                       ORDER BY priority DESC; """)

        # we dont use JOIN's because this code looks better
        # and we dont need fast select

        for category_id, categoryName, cat_priority in cur.fetchall():
            currentCategory = data_classes.ShopCategory(categoryName,
                                                        cat_priority)

            query = """SELECT id, shop, description, short_description,
                       website_link, affiliate_link, placeholder_сolor,
                       priority, tags
                       FROM shops
                       WHERE category_id = %s; """
            cur.execute(query, category_id)

            for (shop_id, shop_name, descr, short_descr,
                 website, affiliate_link, color, priority, tags,) \
                    in cur.fetchall():

                name = shop_name
                description = descr
                short_description = short_descr

                shop_dir = get_part_of_image_dir(website)
                preview_img_link, background_img_link = \
                    get_photos_links(shop_dir)

                website = affiliate_link if affiliate_link else website

                placeholderColor: str = str(color)
                priority: int = int(priority)

                tags: list = json.loads(tags)

                currentShop = data_classes.Shop(
                    name=name,
                    shopDescription=description,
                    shopShortDescription=short_description,
                    websiteLink=website,
                    priority=priority,
                    tags=tags,
                    imageLink=background_img_link,
                    previewImageLink=preview_img_link,
                    placeholderColor=placeholderColor
                )

                query = """SELECT promocode, expiration_date,
                                  adding_date, description
                           FROM promocodes
                           WHERE shop_id = %s; """

                cur.execute(query, (int(shop_id),))

                for (coupon, exp_date, add_date, descr) in cur.fetchall():
                    currentPromo = data_classes.Promocode(
                        coupon=coupon,
                        estimated_date=exp_date,
                        addingDate=add_date,
                        promoCodeDescription=descr,
                    )

                    currentShop.appendPromocode(currentPromo)

                currentShop.sortPromocodesByAddingDate()

                currentShop.parseShortDescriptionByLastAddedPromo()

                currentShop.checkPriority()  # if no promo => prior = 0

                if len(shopCategoriesList) > 0 and \
                        currentShop.name in hot_shops_names:
                    shopCategoriesList[0].appendShop(currentShop)
                    # appending dynamically to hot
                else:
                    currentCategory.appendShop(currentShop)

            currentCategory.sortShopsByPriorityAndLastAddedPromo()

            shopCategoriesList.append(currentCategory)

        cur.close()

    return shopCategoriesList


def _get_banned_json(db: str) -> str:
    # TODO: make json for banned users
    return db


def update_json_db() -> bool:
    try:
        db: list = read_all_db()

        android_json = _get_android_json(db)  # can change db here
        android_json_for_banned_users = _get_banned_json(android_json)

        ios_json = _get_ios_json(db)  # can change db here
        ios_json_for_banned_users = _get_banned_json(android_json)

        with open(constants.android_json, "w") as json_file:
            json_file.write(android_json)
            json_file.flush()

        with open(constants.android_banned_json, "w") as android_banned_file:
            android_banned_file.write(android_json_for_banned_users)
            android_banned_file.flush()

        with open(constants.ios_json, "w") as ios_file:
            ios_file.write(ios_json)
            ios_file.flush()

        with open(constants.ios_banned_json, "w") as ios_banned_file:
            ios_banned_file.write(ios_json_for_banned_users)
            ios_banned_file.flush()

    except Exception as e:
        raise(e)


def _get_shop_id_by_website(shop: data_classes.Shop, cur) -> int:
    query = """SELECT id FROM shops
               WHERE website_link = %s LIMIT 1; """
    args = (shop.websiteLink,)
    cur.execute(query, args)

    id: tuple = cur.fetchone()

    return int(id[0]) if id else 0


def _write_shop(shop: data_classes.Shop,
                category: data_classes.ShopCategory,
                cur) -> int:
    """returns shop_id from db;
       -1 means that shop may be in json but may not be in db
       -2 means that error occured in writing
    """

    id = _get_shop_id_by_website(shop, cur)

    if id:
        return id

    if shop.name and shop.name != " ":

        query = """SELECT id FROM shops
                   WHERE shop = %s LIMIT 1; """
        args = (shop.name,)
        cur.execute(query, args)

        id: tuple = cur.fetchone()

        if id:
            return int(id[0])

    elif not shop.name or shop.name == " ":
        # impossible, but i dont want to delete it
        shop.name = f"{constants.default_shop_name}{randint(0, 1000)}"

    image_dir = get_part_of_image_dir(shop.websiteLink)

    local_img_dir = f"{constants.images_dir_path}{image_dir}"

    if exists(local_img_dir):
        for file in listdir(local_img_dir):
            if file.startswith("prev"):
                filepath = f"{local_img_dir}/{file}"
                shop.placeholderColor: str = \
                    find_placeholder_color(filepath)

    cur.execute("SELECT id FROM categories WHERE category = %s; ",
                category.categoryName)
    row = cur.fetchone()
    if not row:
        raise IndexError(f"No category {category.categoryName}"
                         f"with this index")
    category_id = row[0]

    query = """INSERT INTO shops
               (shop, description, short_description,
                website_link, placeholder_сolor,
                priority, promo_counter, tags, category_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s); """
    args = (shop.name, shop.shopDescription,
            shop.shopShortDescription, shop.websiteLink,
            shop.placeholderColor, shop.priority,
            0, json.dumps(shop.tags, ensure_ascii=False), category_id)

    cur.execute(query, args)

    query = """SELECT id FROM shops
               WHERE shop = %s AND website_link = %s
               LIMIT 1; """
    args = (shop.name, shop.websiteLink,)
    cur.execute(query, args)

    id = cur.fetchone()

    if id:
        return int(id[0])
    else:
        return -2


def _insert_category(category: data_classes.ShopCategory,
                     cur) -> int:
    """returns id of category"""

    if category.categoryName not in constants.categories.values():
        category.categoryName = "Разное"

    cur.execute("SELECT id FROM categories WHERE category = %s; ",
                category.categoryName)

    row = cur.fetchone()
    if row:
        return row[0]

    query = """INSERT INTO categories (category, counter, priority)
               VALUES (%s, %s, %s); """
    cur.execute(query, (category.categoryName, 0, category.priority))
    # NOTE: maybe renamed
    cur.execute("SELECT id FROM categories WHERE category = %s; ",
                category.categoryName)
    return cur.fetchone()[0]


def _write_promocodes(promocodes: set, shop_id: int, cur) -> list:
    promocodes_id = []

    for promocode in promocodes:
        if promocode.coupon in ("", " "):
            continue

        query = """SELECT promocode, shop_id FROM promocodes
                   WHERE promocode = %s AND shop_id = %s; """
        args = (promocode.coupon, shop_id,)
        cur.execute(query, args)

        rows = cur.fetchall()

        if rows and (promocode.coupon, shop_id) in rows:
            # this promo is already in db
            continue

        query = """INSERT INTO promocodes (promocode, expiration_date,
                                           adding_date, description,
                                           source, shop_id)
                   VALUES (%s, %s, %s, %s, %s, %s); """

        args = (promocode.coupon,
                promocode.estimatedDate.strftime('%Y-%m-%d %H:%M:%S'),
                promocode.addingDate.strftime('%Y-%m-%d %H:%M:%S'),
                promocode.promoCodeDescription,
                promocode.source,
                shop_id)

        cur.execute(query, args)

        query = """UPDATE shops
                   SET promo_counter = promo_counter + 1
                   WHERE id = %s; """

        cur.execute(query, (shop_id,))

        query = """SELECT id FROM promocodes
                   WHERE promocode = %s AND shop_id = %s
                   LIMIT 1; """
        args = (promocode.coupon, shop_id)
        cur.execute(query, args)

        fetch = cur.fetchone()

        if fetch:
            promocodes_id.append(int(fetch[0]))

    return promocodes_id


def write_db(promocodes: list,
             shop: data_classes.Shop,
             category: data_classes.ShopCategory,
             is_init: bool = False) -> (int, list):
    """returns (shop_id, promocodes_id)
       if is_init => dont append promocodes"""

    if (not is_init and not promocodes) or any_is_empty(shop, category):
        return (None, None,)

    if isinstance(promocodes, data_classes.Promocode):
        promocodes = [promocodes]

    promocodes = set(promocodes)

    conn = get_connection()
    with conn:
        cur = conn.cursor()
        with cur:

            _insert_category(category, cur)  # returns int category_id

            shop_id: int = 0
            shop_id = _write_shop(shop, category, cur)

            if shop_id < 0:
                return shop_id, None

            if is_init:
                # means we dont need to append promocodes
                return (shop_id, None)

            try:
                promocodes_id: list = _write_promocodes(promocodes,
                                                        shop_id,
                                                        cur)
            except Exception:
                return shop_id, None

    return shop_id, promocodes_id


def _convert_hex_to_rgba(hex_color: str) -> list:
    """hex format: '#ffffff'"""
    try:
        rgba_list = []
        rgba_list.append((int(hex_color[1:3], 16) & 0xFF) / 255.0)  # red
        rgba_list.append((int(hex_color[3:5], 16) & 0xFF) / 255.0)  # green
        rgba_list.append((int(hex_color[5:7], 16) & 0xFF) / 255.0)  # blue
        rgba_list.append(int(1))                                    # opacity
        return rgba_list
    except Exception:
        return [1.0, 1.0, 1.0, 1]


def find_placeholder_color(preview_image: str) -> str:
    try:
        return knn_img_color.colorz(preview_image, 3)[0]
    except Exception:
        return "#ffffff"


def delete_promocodes_by(promo_names: list,
                         shop_name: str) -> bool:

    if any_is_empty(promo_names, shop_name):
        return False

    conn = get_connection()
    with conn:
        cur = conn.cursor()
        with cur:
            query = "SELECT id FROM shops WHERE shop = %s; "
            cur.execute(query, str(shop_name))

            shop_id = cur.fetchone()

            if shop_id:
                shop_id = shop_id[0]
            else:
                return False

            for promo_name in promo_names:
                try:
                    query = """DELETE FROM promocodes
                               WHERE promocode = %s AND shop_id = %s; """
                    args = (promo_name, shop_id)
                    cur.execute(query, args)

                    query = """UPDATE shops
                               SET promo_counter = promo_counter - 1
                               WHERE id = %s; """
                    args = (shop_id)
                    cur.execute(query, args)
                except Exception:
                    continue

    return True


def change_shop_name(old_name: str, new_name: str) -> "str | None":
    if any_is_empty(old_name, new_name) or old_name == new_name:
        return None

    try:
        conn = get_connection()

        with conn:
            cur = conn.cursor()
            with cur:
                query = "UPDATE shops SET shop = %s WHERE shop = %s; "
                args = (new_name, old_name)
                cur.execute(query, args)

    except Exception as e:
        return f"inside change_shop_name: {e}"

    else:
        return "Окс-чпокс"


def set_preview_image(shop_name: str, path_to_photo: str) -> bool:
    """local path to photo"""

    if any_is_empty(shop_name, path_to_photo):
        return False

    conn = get_connection()

    with conn:
        cur = conn.cursor()
        with cur:
            query = """SELECT id FROM shops
                       WHERE shop = %s; """
            args = (shop_name)
            cur.execute(query, args)

            id = cur.fetchone()

            if id:
                id = int(id[0])
            else:
                return False

            placeholder_сolor = find_placeholder_color(path_to_photo)

            query = """UPDATE shops
                       SET placeholder_сolor = %s
                       WHERE id = %s; """
            args = (placeholder_сolor, id)
            cur.execute(query, args)

    return True


def change_coupon(old_coupon: str, new_coupon: str, shop_name: str) -> str:
    if any_is_empty(old_coupon, new_coupon, shop_name):
        return "2empty ;)"

    conn = get_connection()
    with conn:
        cur = conn.cursor()
        with cur:
            query = """SELECT shop_id FROM promocodes
                       WHERE promocode = %s and shop_id = (
                           SELECT id FROM shops WHERE shop = %s
                       ) LIMIT 1; """
            args = (old_coupon, shop_name)
            cur.execute(query, args)

            if not (fetch := cur.fetchone()):
                return "no matches in db"

            shop_id = fetch[0]

            query = """UPDATE promocodes
                       SET promocode = %s
                       WHERE shop_id = %s
                       AND promocode = %s; """
            args = (new_coupon, shop_id, old_coupon)
            cur.execute(query, args)

    return "О'Кейси"


def change_promocode_description(
        shop_name: str,
        promocode: str,
        new_description: str) -> bool:

    if any_is_empty(shop_name, promocode) or len(new_description) < 10:
        return False

    conn = get_connection()
    with conn:
        cur = conn.cursor()
        with cur:
            args = (shop_name,)
            query = """SELECT id FROM shops WHERE shop = %s; """
            cur.execute(query, args)

            shop_id = cur.fetchone()[0]

            query = """UPDATE promocodes SET description = %s
                       WHERE promocode = %s AND shop_id = %s; """
            args = (new_description, promocode, shop_id)
            cur.execute(query, args)

    return True


def change_shop_category(shop_name: str, new_category_name: str) -> bool:
    # all categories must exist
    if not shop_name or \
            (new_category_name not in constants.categories.values()):
        return False

    conn = get_connection()

    with conn:
        cur = conn.cursor()
        with cur:
            query = """UPDATE shops
                       SET category_id = (
                           SELECT id FROM categories WHERE category = %s
                       )
                       WHERE shop = %s; """
            args = (new_category_name, shop_name)
            return bool(cur.execute(query, args))


def delete_shop(shop_name: str) -> bool:
    if not shop_name:
        return False

    conn = get_connection()

    with conn:
        cur = conn.cursor()
        with cur:
            query = """DELETE FROM shops WHERE shop = %s; """
            args = (shop_name)
            return bool(cur.execute(query, args))


def get_priorities() -> str:
    """
    return format is: ('category', priority, 'shop name')
    """

    conn = get_connection()

    with conn:
        cur = conn.cursor()

        with cur:
            cur.execute("""SELECT c.category, s.shop, s.priority
                           FROM categories as c
                           INNER JOIN shops as s
                               ON s.category_id = c.id
                           ORDER BY c.category ASC, s.priority DESC; """)

            priorities = "\n".join([str(line) for line in cur.fetchall()])

    return priorities


def change_priority(shop_name: str, priority: int) -> bool:
    priority = int(priority)

    if priority not in constants.priorities.values() or not shop_name:
        return False

    conn = get_connection()

    with conn:
        cur = conn.cursor()

        with cur:
            query = """UPDATE shops SET priority = %s WHERE shop = %s; """

            cur.execute(query, (priority, shop_name,))

    return True


def _get_hot_shop_names(cur) -> list:
    """returns list[str] with shopnames that must be in HOT category"""
    promo_valid_seconds_default = \
        constants.days_promocode_is_valid * 24 * 60 * 60

    cur.execute("""SELECT DISTINCT shop_id
                   FROM promocodes
                   WHERE (
                       UNIX_TIMESTAMP(expiration_date) -
                       UNIX_TIMESTAMP(adding_date)
                   ) != %s
                   AND
                       DATE(adding_date) <= CURDATE()
                   ORDER BY expiration_date ASC
                   LIMIT 10; """, (promo_valid_seconds_default,))

    hot_shops_indices = cur.fetchall()

    if not hot_shops_indices:
        # FIXME: a bug when no promocodes with known exp date
        return []

    # dict is ordered by default since python 3.7
    # so thats why using dict instead of set
    id_dict = {shop_id: None for (shop_id,) in hot_shops_indices}

    query = """SELECT 6 - COUNT(*) FROM shops
               WHERE category_id = (
                   SELECT id FROM categories
                   WHERE category = %s
               );"""
    args = ("ГОРЯЧЕЕ 🔥", )
    cur.execute(query, args)

    count_insert2hot_automatically: tuple = cur.fetchone()

    count_insert2hot_automatically = abs(count_insert2hot_automatically[0]) if count_insert2hot_automatically else 0

    hot_shops_indices = list(id_dict)[:count_insert2hot_automatically]
    # we've got unique ordered by date indices

    cur.execute("""SELECT shop FROM shops
                   WHERE id IN %s; """, (hot_shops_indices,))
    shop_names = cur.fetchall()

    return list(map(lambda name: name[0], shop_names)) if shop_names else []


def get_shops() -> tuple:
    """Returns tuple of tuples in format
        ((shopname, alternative_name), ... )"""
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        with cur:
            cur.execute("""USE promo; """)
            cur.execute("""SELECT shop, alternative_name FROM shops; """)
            return cur.fetchall()
    return []


def get_part_of_image_dir(website: str) -> str:
    lindex = website.find("//") + 2
    rindex = website.rfind(".")
    return website[lindex:rindex]


def get_website(shop: str) -> str:
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        with cur:
            query = """SELECT website_link FROM shops
                       WHERE shop = %s; """
            args = (shop,)
            cur.execute(query, args)

            fetch = cur.fetchone()

    return fetch[0] if fetch else ""


if __name__ == '__main__':
    pass
