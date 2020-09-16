from database import users
from constants import push_cert
from .pyapns.apns import APNs, Frame, Payload
from firebase_admin import initialize_app, messaging
import datetime
import time
import random


firebase_app = initialize_app()


ios_payload = {
    "aps": {
        "alert": {
            "title": None,
            "body": None
        },
        "mutable-content": 1
    },
    "kind": "favorites-updated"
}


ios_payload_from_admin = {
    "aps": {
        "alert": {
            "title": "Заходи к нам🤗",
            "body": "У нас много новых классных промокодов!"
        },
        "mutable-content": 1
    }
}


def chunks(lst: list, batch_size: int):
    """Yield successive n-sized chunks from lst"""
    for i in range(0, len(lst), batch_size):
        yield lst[i:i + batch_size]


def send_admins_push_notifications(title: str, body: str):
    all_ios_tokens, all_android_tokens = users.get_all_tokens()

    ios_payload_from_admin['aps']['alert']['title'] = title
    ios_payload_from_admin['aps']['alert']['body'] = body

    _send_ios_notifications_from_admin(all_ios_tokens, ios_payload_from_admin)

    return 'ok'


def send_push_notifications(new_shops_indices: list,
                            coupon_description: str = None):
    """if coupon_descr then it will be send to everybody"""
    if isinstance(new_shops_indices, int):
        new_shops_indices = [new_shops_indices]

    ios_tokens_shops, android_tokens_shops = \
        get_tokens_that_like_shops(new_shops_indices)

    _send_ios_notifications(ios_tokens_shops, coupon_description)

    _send_android_notification(android_tokens_shops, coupon_description)


def get_tokens_that_like_shops(new_shops_indices: list) -> (dict, dict):
    new_shops_indices = frozenset(new_shops_indices)

    ios_users_table, ios_links_table = users.get_tables(is_ios=True)
    android_users_table, android_links_table = users.get_tables(is_ios=False)

    ios_token_shops_dict: 'dict[str:list[str]]' = \
        users.get_tokens_linked_with_shops(new_shops_indices,
                                           ios_users_table,
                                           ios_links_table)

    android_token_shops_dict: 'dict[str:list[str]]' = \
        users.get_tokens_linked_with_shops(new_shops_indices,
                                           android_users_table,
                                           android_links_table)

    return ios_token_shops_dict, android_token_shops_dict


def _get_ios_server():
    return APNs(use_sandbox=False, cert_file=push_cert, key_file=push_cert)


def _send_ios_notifications(token_shops: dict, coupon_descr: 'str | None'):
    if not token_shops:
        return

    server = _get_ios_server()

    frame = Frame()

    expiry = int(time.time() + 3600)
    priority = 10

    for token, shops in token_shops.items():
        ios_payload['aps']['alert']['title'] = f"{', '.join(shops)}🔥"
        ios_payload['aps']['alert']['body'] = coupon_descr or "Смотри подробнее в приложении!"
        payload = Payload(custom=ios_payload)
        identifier = random.getrandbits(32)
        frame.add_item(token, payload, identifier, expiry, priority)

    server.gateway_server.send_notification_multiple(frame)


def _send_ios_notifications_from_admin(tokens: list, payload: dict):
    server = _get_ios_server()

    frame = Frame()

    expiry = int(time.time() + 3600)
    priority = 10
    payload = Payload(custom=payload)

    for token in tokens:
        identifier = random.getrandbits(32)
        frame.add_item(token, payload, identifier, expiry, priority)

    server.gateway_server.send_notification_multiple(frame)


def delete_invalid_ios_tokens() -> int:
    tokens_to_delete = []

    feedback_connection = _get_ios_server()

    for token_hex, fail_time in feedback_connection.feedback_server.items():
        tokens_to_delete.append(token_hex.decode('utf-8'))

    return users.delete_tokens(tokens_to_delete, is_ios=True)


def _send_android_notification(token_shops: dict, coupon_description: str):
    if not token_shops:
        return

    body = coupon_description or "Смотри подробнее в приложении!"

    android_params = messaging.AndroidConfig(
        ttl=datetime.timedelta(seconds=3600),
        priority='high'
    )

    failed_tokens = []

    for chunk in chunks(list(token_shops.items()), 500):
        registration_tokens = []

        for token, shops in chunk:
            registration_tokens.append(token)

            notification = messaging.Notification(
                title=f"Новый купон в {', '.join(shops)}🔥",
                body=body
            )

            multicast_message = messaging.MulticastMessage(
                notification=notification,
                android=android_params,
                tokens=registration_tokens,
            )

        batch_failed_tokens = _send_firebase_request(registration_tokens,
                                                     multicast_message)
        failed_tokens.extend(batch_failed_tokens)
        batch_failed_tokens = []

    users.delete_tokens(failed_tokens, is_ios=False)


def _send_firebase_request(
        registration_tokens: list,
        multicast_message
        ) -> list:
    """sends notification via firebase app
    returns list[str] of failed tokens"""
    response = messaging.send_multicast(multicast_message)

    failed_tokens = []

    if response.failure_count > 0:
        responses = response.responses
        for idx, resp in enumerate(responses):
            if resp.exception.code in ("INVALID-REGISTRATION-TOKEN",
                                       "REGISTRATION-TOKEN-NOT-REGISTERED",
                                       "INVALID-RECIPIENT",
                                       "INVALID_ARGUMENT",
                                       "NOT_FOUND"):
                failed_tokens.append(registration_tokens[idx])

    return failed_tokens


if __name__ == '__main__':
    pass
