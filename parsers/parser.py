from abc import ABC, abstractmethod

import datetime
from bs4 import BeautifulSoup as bs
import Levenshtein as levenshtein
from fuzzywuzzy import fuzz

import data_classes
import ml
from constants import days_promocode_is_valid
from database import get_shops

from .html_getter import HTMLGetter, re
from . import parser_constants


def has_promocode(text: str,
                  keywords=parser_constants.ru_promo_keywords,
                  forbidden_words=parser_constants.forbidden_words
                  ) -> bool:

    text = text.lower()

    if any(forbidden_word in text for forbidden_word in forbidden_words):
        return False
    elif any(keyword in text for keyword in keywords):
        return True
    else:
        return False


def has_at_least2promocodes(text) -> bool:
    promo_pat = r"(по )?(([Пп]ромокод[уы]?:?)|"\
                r"([Кк]упон[уы]?:?)|"\
                r"([Сс]кидк[аи]?))"
    promo_ctr = len(re.findall(promo_pat, text))

    return promo_ctr >= 5


class Parser(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def extract_info(self):
        pass

    @abstractmethod
    def extract_promocodes(self, text):
        pass

    @abstractmethod
    def extract_shop(self,
                     shop_url: str,
                     html_text: str = None) -> data_classes.Shop:
        """NOTE: doesnt follow the link here
        shop_url must be final"""

        if shop_url in parser_constants.forbidden_shop_links:
            raise AttributeError("shop_url in forbidden_shop_links")

        try:
            if not html_text:
                request = HTMLGetter.get_request(shop_url)
                # shop_url = request.url
                request.encoding = 'utf-8'
                html_text = request.text

            soup = bs(html_text, 'lxml')

            self.shop_website_text = soup.text

            shop_description: str = self._parse_shop_description(soup)

            try:
                shop_short_description = soup.title.text.lstrip().rstrip()
            except AttributeError:
                shop_short_description = ""  # if no title

        except Exception as e:
            raise(e)
            return None

        shop_name = self.parse_shop_name([shop_short_description,
                                          shop_description])
        # at least 2 descriptions!!!

        if not shop_name or shop_name == " ":
            shop_name = HTMLGetter.get_domain(shop_url)

        if shop_name in parser_constants.forbidden_shop_names:
            raise AttributeError("shop_name in forbidden_shop_names")

        shop_url = parser_constants.same_websites.get(shop_url, shop_url)

        if not shop_description and shop_short_description:
            shop_description = shop_short_description
        elif not shop_description:
            shop_description = shop_name

        if not shop_short_description:
            shop_short_description = shop_name

        tags: list = ml.TagsGetter(shop_short_description).tags \
            if shop_short_description else []
        # IDEA: maybe parse from meta name keywords

        tags = set(tags)
        tags.discard(shop_name)  # iOS requirement
        tags = list(tags)

        preview_img_link = self._parse_save_logo(shop_url, soup)

        background_img_link = self._parse_save_background_img(shop_url,
                                                              shop_name)

        return data_classes.Shop(
            name=shop_name,
            shopDescription=shop_description,
            shopShortDescription=shop_short_description,
            websiteLink=shop_url,
            tags=tags,
            imageLink=background_img_link,
            previewImageLink=preview_img_link,
            placeholderColor="#ffffff"
        )

    @classmethod
    def get_promocodes(self, text: str, patterns: tuple) -> list:
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if len(matches) == 0:
                continue
            else:
                break
        return matches

    def extract_category(self) -> data_classes.ShopCategory:
        if self.shop_website_text:
            category_name = \
                ml.HTMLShopsClassifier(self.shop_website_text).category
        else:
            category_name = "Разное"
        shop_category = data_classes.ShopCategory(categoryName=category_name)
        return shop_category

    def _parse_shop_description(self, soup: bs) -> str:
        match = soup.head.find("meta", {"name": "description"}) \
            if soup.head else ""

        if match:
            shop_description = match['content'].lstrip(' \n\r\t')
            shop_description = re.sub(r"(\!|\.{2,3})", ".", shop_description)

            dot_rindex = len(shop_description)
            iter_ctr = 0
            # shorten shop descr, splitting by sentences
            while dot_rindex > 110 and iter_ctr <= 2:
                iter_ctr += 1
                dot_rindex = shop_description.rfind('. ', 0, dot_rindex)

            shop_description = shop_description[:dot_rindex + 1]

        else:
            match = soup.head.find("meta", {"name": "keywords"}) \
                    if soup.head else ""

            if match:
                shop_description = match['content'].lstrip(' \n\r\t')

            else:
                shop_description = ""

        return shop_description

    def _get_manifest(self, soup) -> str:
        # manifest is json file config that may contain logo
        # soup.find_all()
        return ""

    def _parse_save_logo(self, url: str, soup: bs) -> str:
        """
        returns local path to saved file
        if not found returns ''
        """
        manifest = self._get_manifest(soup)

        if manifest:
            # get manifest['logos']
            # search for some
            pass

        return ""

    def _parse_save_background_img(self, url, shop_name) -> str:
        return ""

    def parse_shop_name(self, descriptions: list) -> str:
        """at least 2 descriptions"""
        for description in descriptions:
            shop_name = ml.TextExtractor(description).shop_name
            if shop_name:
                return shop_name

        return self._parse_shop_name_from_regexp(descriptions[0],
                                                 descriptions[1])

    def _parse_shop_name_from_regexp(self,
                                     shop_short_description: str,
                                     shop_description: str) -> str:

        def parse_name_from(description: str) -> 'str | None':
            res = None

            try:
                left_name = re.findall(parser_constants.left_oriented_pattern,
                                       description)[0]

            except Exception:
                left_name = None

            try:
                rigth_name = \
                    re.findall(parser_constants.rigth_oriented_pattern,
                               description)[0]

            except Exception:
                rigth_name = None

            try:
                if any(domain in rigth_name
                       for domain in parser_constants.domains):

                    return rigth_name

                if any(domain in left_name
                       for domain in parser_constants.domains):

                    return left_name

                if len(left_name) > len(rigth_name):
                    res = rigth_name

                else:
                    res = left_name

            except Exception:
                pass

            return res

        en_shop_name_pattern = r"[\s\b]*([A-Z][A-Za-z]*[\s\'\’\`\']"\
                               r"*[A-Za-z\`\’\']+)[\s\.\,\;]*"

        quotes_pattern = r"[\«\"\'](.*?)[\»\"\']"

        big_letters_pattern = r"\s*([A-ZА-ЯЁ\-\–\—]{3,})\s*"

        for description in (shop_short_description, shop_description):
            match = re.search(en_shop_name_pattern, description)  # ' Full HD '

            if match:
                return match.group(1).lstrip().rstrip(' -–—.,;')

            match = re.search(quotes_pattern, description)  # ' "Хабр" '

            if match:
                return match.group(1)

            match = re.search(big_letters_pattern, description)  # ' МТС '

            if match:
                return match.group(1)

            shop_name = parse_name_from(description)

            if shop_name:
                return shop_name

        return shop_short_description

    @classmethod
    def parse_date(self,
                   text: str,
                   default_days_valid: int = days_promocode_is_valid
                   ) -> datetime.datetime:

        expiration_date = ml.TextExtractor(text).promocode_expiration_date

        if expiration_date:
            return expiration_date

        text = text.lower()

        now = datetime.datetime.now()
        current_year: int = now.year
        current_month: int = now.month

        if ' завтра' in text:
            return datetime.datetime.now() + datetime.timedelta(days=1)

        if ' сегодня' in text:
            return datetime.datetime.now()

        if 'до конца лета' in text:
            return datetime.datetime(current_year, 8, 31)

        if 'до конца осени' in text:
            return datetime.datetime(current_year, 11, 30)

        if 'до конца года' in text:
            return datetime.datetime(current_year, 12, 31)

        if 'до конца зимы' in text:
            if current_month == 12:
                return datetime.datetime(current_year + 1, 2, 28)
            else:
                return datetime.datetime(current_year, 2, 28)

        if 'до конца весны' in text:
            return datetime.datetime(current_year, 5, 31)

        pat = r"(?:действует|работает) [а-я ]{0,11}(\d+) дней"

        if (match := re.search(pat, text)):
            return datetime.datetime.now() + \
                datetime.timedelta(days=match.group(1))

        for month_index, month in enumerate(parser_constants.ru_months):
            entry_index = text.find(month)

            if entry_index != -1:  # if found

                if " конц" in text:
                    # "до конца марта"
                    if month == " январ" and current_month in (11, 12):
                        # HAPPY NEW YEAR!!11!
                        current_year += 1

                    return datetime.datetime(
                        current_year,
                        month_index + 1,
                        parser_constants.days_in_month[month_index]
                    )

                elif " начал" in text:
                    if month == " январ" and current_month in (11, 12):
                        # HAPPY NEW YEAR!!11!
                        current_year += 1
                    return datetime.datetime(current_year,
                                             month_index + 1,
                                             1)

                else:
                    # month found
                    # "до 23 марта"
                    # ______^______ is entry_index
                    # ___^_________ is entry_index - 2

                    entry_index -= 2  # sub len of day in text

                    try:
                        day = abs(int(text[entry_index:entry_index + 2]))
                    except ValueError:
                        # 'до3 марта' - if error in text and month in 1..9
                        try:
                            day = abs(int(
                                text[entry_index + 1:entry_index + 2]
                            ))
                        except ValueError:
                            pass
                        else:
                            return datetime.datetime(current_year,
                                                     month_index + 1,
                                                     day)
                    else:
                        return datetime.datetime(current_year,
                                                 month_index + 1,
                                                 day)

        # if we're here => not found before
        matches = re.findall(parser_constants.date_pattern, text)

        if matches:
            match = matches[0]
            day, month, year = match  # tuple here
            day, month = int(day), int(month)
            year = int(year) if int(year) > 2000 else int(f"20{year}")
            return datetime.datetime(year, month, day)

        short_date_pattern = r"[\s](\d{1,2})[-./](\d{1,2})[\s\!\.\,]"
        matches = re.findall(short_date_pattern, text)

        if matches:
            day, month = matches[0]
            day, month = int(day), int(month)
            year = int(current_year)
            if 1 <= month <= 12 and 1 <= day <= 31:
                return datetime.datetime(year, month, day)

        return datetime.datetime.now() + \
            datetime.timedelta(days=default_days_valid)

    @abstractmethod
    def set_default_priority(self):
        pass

    @classmethod
    def search4shopname(self, text: str) -> str:  # test
        """
        Returns:
            str shopname if found
            '' if not found
        """

        shops = {s[0]: (s[0].lower(), s[1].lower()) for s in get_shops()}
        # {shop: (name_lower, alternative_name_lower)}

        text = text.lower()
        text = re.sub(r"[^a-zа-яё0-9\n ]", " ", text)
        text = re.sub(r"[ ]+", " ", text)
        text = f" {text} "  # adding spaces for correct partial ratio searching

        trust_ratio = 82

        corresponding_shop = ""
        max_ratio = 0

        for line in text.split('\n'):
            for shopname, (shopname_lower, alternative_name_lower) \
                    in shops.items():

                main_partial_ratio = fuzz.partial_ratio(
                    line,
                    f" {shopname_lower} "
                )

                if alternative_name_lower:
                    alternative_partial_ratio = fuzz.partial_ratio(
                        line,
                        f" {alternative_name_lower} "
                    )
                else:
                    alternative_partial_ratio = 0

                partial_ratio = max(
                    main_partial_ratio,
                    alternative_partial_ratio
                )

                if partial_ratio > max_ratio and partial_ratio > trust_ratio:
                    corresponding_shop = shopname
                    max_ratio = partial_ratio

        return corresponding_shop

    @classmethod
    def shorten_links(self, text: str) -> str:
        link_pattern = r"((https?:\/\/)?"\
                       r"([\da-z\.-]+)\.([a-z\.]{2,6})"\
                       r"([\/\w\.\?\:\=\%\&-]*)*\/?)"
        links = re.findall(link_pattern, text)

        for link, _, _, _, _ in links:
            if len(link) > parser_constants.max_link_len:
                # width of iphone screen
                try:
                    req = HTMLGetter.get_request(f"https://clck.ru/--?url={link}")
                    new_link = req.text.replace("https://", "")
                    text = text.replace(link, new_link)
                except Exception:
                    continue
        return text

    @classmethod
    def is_valid_promocode_morph_check(self, promocode: str) -> bool:
        parsed_promo = ml.morph.parse(promocode)[0]
        if parsed_promo.tag.POS not in ('VERB', 'ADJS', 'PRCL', 'PRED', ):
            return True
        elif parsed_promo.tag.POS == 'VERB' and \
                (promocode.isupper() or promocode.startswith('#')):
            return True
        else:
            return False

    def clear_text(self, text: str) -> str:
        promocode_description = re.sub(r" +", " ", text)
        promocode_description = re.sub(r"\n+", "\n", promocode_description)
        # promocode_description = re.sub(r"[\'\•\"\«\»]", "",
        #                                promocode_description)

        # deleting emoji from text and non-visible symbols from text
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

        return promocode_description
