from quart import Quart, request
import asyncio
from telethon import TelegramClient

import constants
from web import serve_tg_bot
from database import users


app = Quart(__name__)


API_ID = 0
API_HASH = 'secret'
SESSION = 'secret'


def is_user_valid(headers) -> bool:
    if headers.get('Remote-Addr', "") != constants.nginx_host or \
            headers.get('Callback-Header', "") != "secret":
        return False
    else:
        return True


def is_ios_device(headers) -> bool:
    user_agent = headers.get('User-Agent', "")
    if "Darwin" in user_agent:
        os = "ios"
    elif "Android" in user_agent:
        os = "android"
    else:
        raise AttributeError("wrong user-agent")

    return os == "ios"


@app.before_serving
async def run_telegram():
    try:
        asyncio.ensure_future(serve_tg_bot())
        return 'Success'
    except Exception as e:
        raise(e)
        return 'fail'


@app.route("/", methods=['GET'])
async def index():
    if not is_user_valid(request.headers):
        return 'not valid'
    else:
        return 'ok'


@app.route('/promocode', methods=['POST'])
async def post_promocode():
    if not is_user_valid(request.headers):
        return 'not valid'

    form = await request.get_json()

    try:
        promocode = form['promocode']
    except Exception:
        return 'cant get value from dict'

    res_coupon = f"предложен промокод:\n{promocode}\n" \
                 f"ip: {request.headers.get('X-Real-IP', 'cant get ip')}"

    async with TelegramClient(SESSION, API_ID, API_HASH) as client:
        await client.send_message(admin, res_coupon)

    return 'ok'


@app.route('/feedback', methods=['POST'])
async def post_feedback():

    if not is_user_valid(request.headers):
        return 'not valid'

    form = await request.get_json()

    try:
        feedback = form['feedback']
    except Exception:
        return 'cant get value from dict'

    try:
        is_ios = is_ios_device(request.headers)
    except AttributeError:
        return "not saved"

    system = "ios" if is_ios else "android"

    res_feedback = f"feedback:\n{feedback}\n" \
                   f"ip: {request.headers.get('X-Real-IP', 'cant get ip')}\n" \
                   f"system: {system}"

    async with TelegramClient(SESSION, API_ID, API_HASH) as client:
        await client.send_message(admin, res_feedback)

    return 'ok'


@app.route('/add_user_info', methods=['POST'])
async def post_user_info():

    if not is_user_valid(request.headers):
        return 'not valid'

    try:
        is_ios = is_ios_device(request.headers)
    except AttributeError:
        return "not saved"

    form = await request.get_json()

    try:
        token = form['deviceToken']
        favorite_shops = form['favoriteShops']
        is_user_active: bool = form['userPreferPush']
    except KeyError:
        return 'cant get value from dict'

    user_ip = request.headers.get('X-Real-IP', '')

    async with TelegramClient(SESSION, API_ID, API_HASH) as client:
        debug_info = f"token: {token}\n" \
                     f"favorite_shops: {favorite_shops}\n" \
                     f"is_active: {is_user_active}"
        await client.send_message(admin, debug_info)

    await users.insert_user_info(
        token,
        favorite_shops,
        is_user_active,
        is_ios,
        user_ip=user_ip
    )

    return 'ok'


if __name__ == '__main__':
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8686)), debug=True)
