import json
from datetime import datetime, timedelta
from os.path import exists
from os import remove

from .utils import get_connection
import data_classes
import constants


def append_ads(image_path: str,
               website: str,
               category: str,
               priority: int,
               days_valid_since_today: int
               ) -> bool:
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        with cur:
            cur.execute("""SELECT category FROM categories
                           ORDER BY priority DESC; """)

            categories = list(map(lambda c: c[0], cur.fetchall()))

            insert_after_category_index: int = categories.index(category)

            expiration_date = datetime.now() + \
                timedelta(days=days_valid_since_today)

            query = """INSERT INTO ads
                       (insert_after_category_index, ads_image, priority,
                        expiration_date, website)
                       VALUES (%s, %s, %s, %s, %s); """

            args = (insert_after_category_index, image_path, priority,
                    expiration_date.strftime('%Y-%m-%d %H:%M:%S'),
                    website,)

            cur.execute(query, args)

        return True


def remove_ads(category_index: int, website_link: str) -> str:
    try:
        conn = get_connection()
        with conn:
            cur = conn.cursor()
            with cur:
                query = """SELECT ads_image FROM ads
                           WHERE
                           insert_after_category_index = %s
                           AND
                           website = %s
                           LIMIT 1; """
                args = (category_index, website_link,)
                cur.execute(query, args)

                img = cur.fetchone()

                if not img:
                    return f"not img, not deleted; "\
                           f"{category_index}, {website_link}"

                img_path = f"{constants.static_data}{img[0]}"

                if exists(img_path):
                    remove(img_path)
                else:
                    return f"very strange... photo not exists; "\
                           f"{category_index}, {website_link}\n{img_path}"

                query = """DELETE FROM ads
                           WHERE
                           insert_after_category_index = %s
                           AND
                           website = %s; """
                args = (category_index, website_link,)
                cur.execute(query, args)

        return 'ok'

    except Exception as e:
        return f"{str(e)} in remove_ads"


def _jsonify_ads() -> json:
    try:
        conn = get_connection()
        with conn:
            cur = conn.cursor()
            with cur:
                cur.execute("""DELETE FROM ads
                               WHERE DATE(expiration_date) < CURDATE(); """)

                cur.execute("""SELECT insert_after_category_index,
                               ads_image, priority, website
                               FROM ads
                               ORDER BY insert_after_category_index ASC; """)

                last_idx = -1
                ads_category = None

                ads_classes_list = []

                for category_idx, img, priority, website in cur.fetchall():
                    if category_idx != last_idx:
                        if ads_category:
                            ads_classes_list.append(ads_category)
                        ads_category = data_classes.AdsInCategory(category_idx)
                        last_idx = category_idx
                    img = f"{constants.server_addr}/{img}"
                    ads = data_classes.Ads(img, website, priority)
                    ads_category.append_ads(ads)
                if ads_category:
                    # finally
                    ads_classes_list.append(ads_category)

                ads_json = json.dumps(ads_classes_list,
                                      default=lambda obj: obj.__dict__,
                                      ensure_ascii=False,
                                      check_circular=True,
                                      allow_nan=False,
                                      indent=1)

        return ads_json

    except Exception:
        return "[]"


def save_ads_json() -> str:
    try:
        ads_json: str = _jsonify_ads()

    except Exception as e:
        return f"{str(e)}, in _jsonify_ads"

    else:
        with open(constants.ios_ads_json_path, 'w') as ios_ads_file:
            ios_ads_file.write(ads_json)
            ios_ads_file.flush()

        with open(constants.android_ads_json_path, 'w') as android_ads_file:
            android_ads_file.write(ads_json)
            android_ads_file.flush()

        return ads_json
