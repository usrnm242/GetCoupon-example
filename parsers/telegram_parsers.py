from constants import priorities, tg_sources

from .html_getter import HTMLGetter, re
from .parser import Parser, data_classes
from . import parser_constants


class TelegramParser(Parser):
    def __init__(self,
                 text: str,
                 shop_url: str = None,
                 follow_redirect=True,
                 **kwargs):
        self.promocodes: list = None
        self.shop = None
        self.shop_category = None
        self.text = self.clear_text(text)
        self.text = self.replace_links(self.text).lstrip().rstrip()
        self.shop_url, self.shop_website_text = "", ""
        self.source = self.get_source(**kwargs)

        if shop_url:
            if follow_redirect:
                shop_url, shop_html = HTMLGetter.follow_redirect(shop_url)
                shop_url = HTMLGetter.cut_utm_from_url(shop_url)
                shop_url = HTMLGetter.get_root_website(shop_url)
                self.shop_url, self.shop_website_text = shop_url, shop_html
        else:
            link = re.search(parser_constants.link_pattern, self.text)
            if link:
                self.shop_url, self.shop_website_text = \
                    HTMLGetter.follow_redirect(link[0])
                self.shop_url = HTMLGetter.get_root_website(self.shop_url)
            else:
                # raise(AttributeError(f"No link in {self.text}"))
                pass

        self.text = Parser.shorten_links(self.text)

    def get_source(self, **kwargs) -> str:
        source = kwargs.get('channel_id', '')
        source: str = tg_sources.get(source, '')
        return source

    def clear_text(self, promocode_description: str) -> str:
        # TODO: make from superclass
        promocode_description = re.sub(r" +", " ", promocode_description)
        promocode_description = re.sub(r"\n+", "\n", promocode_description)
        promocode_description = re.sub(r"[\'\•\"\«\»]", "",
                                       promocode_description)

        # deleting emoji from text
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            u"\U0001f926-\U0001f937"
            u'\U00010000-\U0010ffff'
            u"\u200b"  # non visible fucking symbols start
            u"\u200c"
            u"\u200d"
            u"\uFEFF"
            u"\u2060-\u2063"  # non visible fucking symbols end
            u"\u2640-\u2642"
            u"\u2600-\u2B55"
            u"\u23cf"
            u"\u23e9"
            u"\u231a"
            u"\u3030"
            u"\ufe0f"
            "]+", flags=re.UNICODE)

        promocode_description = emoji_pattern.sub(r'', promocode_description)
        promocode_description = self.delete_non_informational_symbols(promocode_description)

        return promocode_description

    def delete_non_informational_symbols(self,
                                         promocode_description: str) -> str:
        # here we delete by lines
        lines = []

        for line in promocode_description.split('\n'):
            # deleting non-needed lines from descr
            if any(word in line for word in ("t.me", "#", "chat", "@")):
                continue

            lines.append(line.rstrip().lstrip())

        promocode_description = '\n'.join(lines)
        del lines
        return promocode_description

    def extract_info(self) -> tuple:
        self.promocodes: list = self.extract_promocodes()

        if not self.promocodes:
            raise(AttributeError("not promocodes"))

        self.shop = self.extract_shop()

        if not self.shop:
            raise(AttributeError("not shop"))

        self.set_default_priority()

        self.shop_category = self.extract_category()

        if not self.shop_category:
            raise(AttributeError("not shop_category"))

        return self.promocodes, self.shop, self.shop_category

    def set_default_priority(self):
        self.shop.priority = priorities['default']

    @classmethod
    def replace_links(self, promocode_description: str) -> str:
        last_uri = ''

        for link in re.finditer(
                parser_constants.link_pattern,
                promocode_description):

            if not link:
                continue

            full_match, schema, uri = link.group(1), link.group(2), link.group(3)

            if uri == last_uri:
                # we had already replaced this link
                continue
            else:
                last_uri = uri

            if not schema:
                # no http prefix
                url = f"https://{full_match}"
            else:
                url = full_match

            new_url, _ = HTMLGetter.follow_redirect(url)
            new_url = HTMLGetter.cut_utm_from_url(new_url)
            promocode_description = re.sub(
                full_match,
                new_url,
                promocode_description,
            )

        return promocode_description

    def extract_promocodes(self) -> list:
        promocode_description = self.text
        promocodes: list = \
            self.get_promocodes(promocode_description,
                                parser_constants.telegram_patterns)

        for p in promocodes:
            if p and (len(p) >= 3 or (p.isdigit() and len(p) >= 2)) and \
                    p not in parser_constants.telegram_promo_stop_words:
                promocode = p
                if self.is_valid_promocode_morph_check(promocode):
                    break
        else:
            return []

        if any(forbidden_promocode in promocode.lower()
               for forbidden_promocode in
               parser_constants.forbidden_promocodes):

            return []

        expiration_date = self.parse_date(promocode_description)

        for key in parser_constants.replacement_table.keys():
            promocode_description = \
                promocode_description.replace(
                    key, parser_constants.replacement_table[key]
                )

        return [data_classes.Promocode(
                    coupon=promocode,
                    promoCodeDescription=promocode_description,
                    estimated_date=expiration_date,
                    source=self.source
                    )
                ]

    def extract_shop(self) -> 'data_classes.Shop | None':
        if self.shop_url:
            return super().extract_shop(self.shop_url)
        else:
            shopname = self.search4shopname(self.text)
            return data_classes.Shop(shopname, "", "", "") if shopname else None


class TelegramParserSplitter(TelegramParser):
    def __init__(self, text: str, links: list = None, **kwargs):
        # OPTIMIZE: store html from every link
        super(TelegramParserSplitter, self).__init__("")
        self.text = self.replace_links(text)
        self.links = links
        self.extractor = TelegramParser
        self.source = self.get_source(**kwargs)

    def extract_info(self) -> zip:
        """returns:
            zip[data_classes.Promocode,
                data_classes.Shop,
                data_classes.ShopCategory]
        """
        return self.get_splitted_text(self.text)

    def search4shoplink(self, text: str) -> str:
        """returns shoplink if found else ''"""
        match = re.search(parser_constants.link_pattern, text)
        return match[0] if match else ""

    def get_splitted_text(self, text: str) -> zip:
        """returns:
            zip[data_classes.Promocode,
                data_classes.Shop,
                data_classes.ShopCategory]"""
        texts = text.split("\n\n") if len(text) > 150 else [text]
        # shop names in every split
        shops_names = ["" for _ in range(len(texts))]
        shops_categories = [None for _ in range(len(texts))]

        for text_index, text in enumerate(texts):
            shopname = self.search4shopname(text)
            if shopname:
                shops_names[text_index] = data_classes.Shop(shopname,
                                                            "", "", "")
                shops_categories[text_index] = \
                    data_classes.ShopCategory("Разное")
                # it will work with promo_db
                # automatically pasts in right place
                # because this shop is already in db
            else:
                shop_url = self.search4shoplink(text)
                if shop_url:
                    try:
                        parser = self.extractor(text, shop_url)
                        shop: data_classes.Shop = parser.extract_shop()
                        category: data_classes.ShopCategory = \
                            parser.extract_category()
                    except Exception:
                        continue

                    shops_names[text_index] = shop
                    shops_categories[text_index] = category

        res_texts, res_shops, res_categories = [], [], []

        current_text = ""
        current_detected_name = None
        current_category = None

        filled_first = False
        appended_after_detected = 0

        for text, shop_name, category in zip(texts,
                                             shops_names,
                                             shops_categories):
            if not shop_name:
                if appended_after_detected > 1:
                    continue
                current_text = f"{current_text}\n\n{text}"
                appended_after_detected += 1
            elif not filled_first and shop_name:
                current_text = f"{current_text}\n\n{text}"
                current_detected_name = shop_name
                current_category = category
                filled_first = True
            elif shop_name == current_detected_name:
                current_text = f"{current_text}\n\n{text}"
            else:
                res_texts.append(current_text)
                res_shops.append(current_detected_name)
                res_categories.append(current_category)
                current_text = text
                current_detected_name = shop_name
        else:
            res_texts.append(current_text)
            res_shops.append(current_detected_name)
            res_categories.append(current_category)

        index = 0
        length = len(res_texts)

        while index < length:
            # OPTIMIZE: BAD CODE
            promocodes = self.extractor(res_texts[index],
                                        shop_url="BAD CODE",
                                        follow_redirect=False) \
                                        .extract_promocodes()
            if not promocodes:
                res_texts.pop(index)
                res_shops.pop(index)
                res_categories.pop(index)
                length -= 1
                continue
            else:
                res_texts[index] = promocodes
                index += 1

        return zip(res_texts, res_shops, res_categories)
