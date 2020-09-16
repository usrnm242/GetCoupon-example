import vk
from constants import vk_targets
from parsers import SocialNetworkParser, SocialNetworkSplitterParser, \
     has_promocode, has_at_least2promocodes


def run_vk_client():
    API_KEY = "086ab88a0a2fae5ac549199a404703573558c44732"\
              "2e17ea90e8aaa98b983540bd369932bcf9089d17cf7"

    session = vk.Session(access_token=API_KEY)
    api = vk.API(session, timeout=60)

    for group_domain in vk_targets:
        print(group_domain)
        wall_content: dict = api.wall.get(domain=group_domain,
                                          count=10,
                                          v='5.120')
        try:
            text = wall_content['items'][0]['text']
        except TypeError:
            print("FUCK FUCK FUCK, TypeError in vk parser")
            continue

        if has_promocode(text):
            if has_at_least2promocodes(text):
                print("has_at_least2promocodes")
                # res = SocialNetworkSplitterParser(text).extract_info()
                # res = list(res)
                continue
            else:
                print("has 1 promo")
                promocode, shop, category = \
                    SocialNetworkParser(text).extract_info()
                print(promocode, shop, end='\n\n\n')
        else:
            print("no promo")
