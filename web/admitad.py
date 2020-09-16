import requests
import csv
import datetime
from time import sleep
from collections import defaultdict
import re
from telethon.sync import TelegramClient

import data_classes
from database import write_db, db_getter, db_writer


ru_alphabet_lower = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
API_ID = 0
API_HASH = ''
SESSION = ''


def is_russian(text: str) -> bool:
    return any(ru_letter in text.lower() for ru_letter in ru_alphabet_lower)


async def _shorten_link_admitad(link: str) -> str:
    response = requests.get(link)
    url_to_shorten = response.url

    async with TelegramClient(SESSION, API_ID, API_HASH) as client:
        await client.send_message('admitad_bot', url_to_shorten)
        sleep(2)
        msg_with_new_link = await client.get_messages('admitad_bot', 1)

    msg_with_new_link = msg_with_new_link[0].to_dict()
    msg_with_new_link = msg_with_new_link['message']

    new_link = re.search(r"Deeplink: (.*)", msg_with_new_link)

    new_link = new_link.group(1) if new_link else link

    return new_link


async def build_promocode(
        row: dict,
        existing_coupons_descriptions: list
        ) -> 'data_classes.Promocode | None':

    coupon = row['promocode']

    if coupon in ('Не нужен',):
        return None

    if isinstance(row['description'], float):
        row['description'] = ""

    for existing_coupon, existing_description in existing_coupons_descriptions:
        if coupon == existing_coupon:
            if any(link in existing_description
                   for link in ('fas.st', 'lite.al', 'lite.bz')):
                return None
            else:
                # coupon_description = await _get_new_description(row)
                coupon_info = await _get_new_coupon_info(row)
                if coupon_info:
                    descr, exp_date = coupon_info
                    db_writer.write_coupon_from_cpa(coupon,
                                                    descr,
                                                    exp_date
                                                    )
                else:
                    return None

    coupon_info = await _get_new_coupon_info(row)
    if not coupon_info:
        # checks here adding date
        return None

    coupon_description, expiration_date = coupon_info

    return data_classes.Promocode(coupon,
                                  expiration_date,
                                  coupon_description)


async def _get_new_coupon_info(row: dict) -> 'tuple | None':
    """Returns (descr: str, exp_date: datetime)
       Returns None if starting_date > NOW()"""
    coupon_description = await _get_new_description(row)  # new coupon here

    expiration_date = _get_expiration_date(row)

    starting_date = _get_starting_date(row)

    if starting_date > datetime.datetime.now():
        return None

    return coupon_description, expiration_date



async def _get_new_description(row: dict) -> str:
    try:
        row['gotolink'] = await _shorten_link_admitad(row['gotolink'])
    except Exception:
        pass

    coupon_description = '\n'.join([row['name'],
                                    row['description'],
                                    row['gotolink']])

    return coupon_description


def _get_expiration_date(row: dict) -> datetime.datetime:
    date = _get_date(row, "date_end")
    if not date:
        now = datetime.datetime.now()
        date = datetime.datetime(now.year, 12, 31)
    return date


def _get_starting_date(row: dict) -> datetime.datetime:
    date = _get_date(row, "date_start")
    if not date:
        date = datetime.datetime.now()
    return date


def _get_date(row: dict, column: str) -> 'datetime.datetime | None':
    if row[column] and row[column] != "None":
        year = int(row[column][:4])
        month = int(row[column][5:7])
        day = int(row[column][8:10])

        date = datetime.datetime(year, month, day)

    else:
        date = None

    return date


def build_shop(row: dict) -> data_classes.Shop:
    shop_website = row['site'] \
        .replace("http://", "https://", 1) \
        .replace("www.", "") \
        .strip("/ ")

    return data_classes.Shop(shop_website.replace("https://", ""),
                             "",
                             "",
                             shop_website)


async def _dict_shops_associated_with_coupons() -> dict:
    existing_coupons_and_descr = db_getter.get_coupons_and_descriptions()

    coupons_csv_url = "http://export.admitad.com/ru/webmaster/websites/......"

    req = requests.get(coupons_csv_url,
                       timeout=10,
                       allow_redirects=False)
    req.encoding = 'utf-8'
    coupons_csv = req.text

    reader = csv.DictReader(coupons_csv.splitlines(), delimiter=';')

    shop_coupons_dict = defaultdict(list)

    for row in reader:

        if not is_russian(row['name']):
            continue

        promocode = await build_promocode(row, existing_coupons_and_descr)

        if not promocode:
            continue

        shop = build_shop(row)

        shop_coupons_dict[shop].append(promocode)

    return shop_coupons_dict


async def write_coupons_from_admitad() -> str:
    """writes to db only coupons from admitad
        Returns: (debug_info: str, shop_indices: list[int])

        debug_info is string with result for admin
            in format 'shop: coupons'

        shop_indices deeded for sending push notifications
    """
    category = data_classes.ShopCategory("Разное")

    res_for_admin = []
    shop_indices = []

    shop_promocodes = await _dict_shops_associated_with_coupons()

    for shop, promocodes in shop_promocodes.items():
        shop_id, promocodes_indices = write_db(promocodes, shop, category)
        shop_indices.append(shop_id)
        coupons = list(map(lambda c: c.coupon, promocodes))
        res_for_admin.append(f"{shop.name}: {coupons}")

    info4admin = '\n'.join(res_for_admin) if res_for_admin else "no new coupons"

    return (info4admin, shop_indices, )


if __name__ == '__main__':
    res = write_coupons_from_admitad()
    print(res)
