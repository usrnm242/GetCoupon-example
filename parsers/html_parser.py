from constants import priorities

from .html_getter import HTMLGetter
from .parser import Parser, data_classes, re, bs  # BeautifulSoup
from . import parser_constants


class HTMLParser(Parser):
    def __init__(self, promo_url: str, soup: bs = None):
        self.promo_url = promo_url
        self.shop_url = HTMLGetter.get_root_website(promo_url)
        self.soup = soup if soup is not None else \
            bs(HTMLGetter.get_request(self.promo_url).text, 'lxml')
        # text from promo ^
        self.shop_website_text = None

        self.promocodes: list = None
        self.shop = None
        self.shop_category = None

    def extract_info(self):
        self.promocodes: list = \
            self.extract_promocodes(self.soup, promo_url=self.promo_url)

        if not self.promocodes:
            raise(AttributeError)

        # FIXME: delete promo url from method
        self.shop = self.extract_shop()
        self.shop_category = self.extract_category()

        if any(item is None for item in
               (self.shop, self.shop_category)):

            raise(AttributeError("any(item is None"))

        self.set_default_priority()

        return self.promocodes, self.shop, self.shop_category

    def set_default_priority(self):
        self.shop.priority = priorities['html']

    def extract_promocodes(self, soup: bs, promo_url: str) -> list:
        promocodes = []

        def get_matches(soup: bs, patterns: tuple) -> list:
            for pattern in patterns:  # r"[по ]?[пП]ромо[\- ]?коду?:?"
                matches: list = soup.find_all(text=re.compile(pattern))
                if not matches:  # no promocodes here
                    continue
                else:
                    return matches
            return matches  # always list

        matches: list = get_matches(soup,
                                    parser_constants.promo_paragraphs_patterns)

        for match in matches:
            promocode_description = match.parent

            search_using_regexp = False

            while True:
                length = len(promocode_description.text)
                if 50 <= length <= 400:
                    break
                elif length > 400:
                    # search paragraph using regex
                    search_using_regexp = True
                    break
                else:
                    promocode_description = promocode_description.parent

            links = []

            if search_using_regexp:
                promocode_description = self.search_paragraph(soup.text)
            else:
                links = promocode_description.find_all("a", href=True)

                if len(links) == 0:
                    links = match.parent.parent.find_all("a", href=True)

                if len(links) > 2:
                    links = links[:2]  # take first 2 of them

                if len(links) > 0:
                    for link in links:
                        if self.shop_url in link:
                            continue
                        partner_website = HTMLGetter.get_request(link['href']).url
                        self.shop_url = \
                            HTMLGetter.get_root_website(partner_website)
                        html = HTMLGetter.get_request(self.shop_url)
                        self.soup = bs(html.text, 'lxml')
                    # if link in text of promo it means
                    # that this link is link to real shop
                    # and current website is partner's website

                promocode_description = \
                    promocode_description.text.lstrip().rstrip()

            if promocode_description is None or \
                    any(stop_word in promocode_description
                        for stop_word
                        in parser_constants.html_promo_stop_words):

                continue

            promocode_description = \
                re.sub(r"[\'\"\•\«\»]", "", promocode_description)

            promo_match = \
                self.get_promocodes(promocode_description,
                                    parser_constants.promocodes_match_pattern)

            if promo_match:
                promocode = promo_match[0]
                if not self.is_valid_promocode_morph_check(promocode):
                    continue
            else:
                continue

            expiration_date = self.parse_date(promocode_description)

            joining_list = [promocode_description]

            for link in links:
                # we're taking first 2 links
                # appending links from html descr to the end of descr text
                joining_list.append(link['href'])

            promocode_description = '\n'.join(joining_list)
            del joining_list

            promocodes.append(data_classes.Promocode(
                coupon=promocode,
                promoCodeDescription=promocode_description,
                estimated_date=expiration_date))

        return promocodes

    def search_paragraph(self, text: str) -> 'str | None':
        match = re.search(parser_constants.promocode_paragraph_pattern, text)
        return match.group(1) if match else None

    def extract_shop(self) -> data_classes.Shop:
        return super().extract_shop(self.shop_url)
