from .telegram_parsers import TelegramParser, TelegramParserSplitter
from .parser import re, data_classes
from . import parser_constants

from constants import priorities


class SocialNetworkParser(TelegramParser):
    """Parses promocodes from social networks posts :)
       Like TelegramParser
       If you've got link on shop, you can attach it in init
    """

    def __init__(self, text, shop_url=None, follow_redirect=True, **kwargs):
        super(SocialNetworkParser, self).__init__(text,
                                                  shop_url,
                                                  follow_redirect,
                                                  **kwargs)

    def delete_non_informational_symbols(self, description: str) -> str:
        # delete just hashtags
        hashtag_pattern = r"\#[\w\d]*\s*"
        return re.sub(hashtag_pattern, "", description)

    def extract_info(self) -> tuple:
        self.promocodes: list = self.extract_promocodes()

        if self.shop_url:
            self.shop = data_classes.Shop("", "", "", self.shop_url)
        else:
            shop_name = self.search4shopname(self.text)
            self.shop = data_classes.Shop(shop_name, "", "", "")

        if not self.promocodes:
            raise(AttributeError("not self.promocodes"))

        if not self.shop:
            raise(AttributeError("not self.shop"))

        self.set_default_priority()

        self.shop_category = data_classes.ShopCategory("Разное")

        return self.promocodes, self.shop, self.shop_category

    def extract_promocodes(self):
        """
        splits by senteces
        in every sentence searches 4 keyword
        if found => search for promocode patterns
        first priority - big letters + numbers with ':'
        then - english letters + numbers with ':'
        then the same without ':'

        Returns: list[data_classes.Promocode]
        """
        promocode_description = self.text

        sentences: list = self._split_by_sentences(promocode_description)

        sentence_with_promocode = promocode_description  # no needed

        promocodes = ()

        for sentence in sentences:
            if any(keyword in sentence.lower()
                   for keyword in ("промокод", "купон", "промо-код", )):

                sentence_with_promocode = sentence

                promocodes: list = \
                    self.get_promocodes(sentence_with_promocode,
                                        parser_constants.instagram_patterns)
                if promocodes:
                    break
                    # TODO:
                    # make probabilities and do not break
                    # continue iter by senteces and search4 promo in every
                    # after that (we know that here is 1 promo)
                    # we can choose the most suitable coupon

        for p in promocodes:
            if p and len(p) >= 3:
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
                )]

    def _split_by_sentences(self, promocode_description: str) -> list:
        promocode_description = re.sub(r"[!.?]", ".", promocode_description)
        senteces = promocode_description.split('.')
        return senteces

    def set_default_priority(self):
        self.shop.priority = priorities['default']


class SocialNetworkSplitterParser(TelegramParserSplitter):
    """
    if text has more than 1 promo then we should split text
    by paragraphs and search 4 coupons in every paragraph
    inherited from TelegramParserSplitter
    method extract_info returns:
        zip[data_classes.Promocode,
            data_classes.Shop,
            data_classes.ShopCategory]
    """

    def __init__(self, text):
        super(SocialNetworkSplitterParser, self).__init__(text)
        self.extractor = SocialNetworkParser
