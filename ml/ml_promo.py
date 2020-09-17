import re
from pymorphy2 import MorphAnalyzer
import pickle
import datetime
from numpy import amax
from abc import ABC, abstractmethod
from natasha import MorphVocab, DatesExtractor
from navec import Navec
from slovnet import NER

import constants

no_needed_words4tags = set(
    ["онлайн", "com", "ташир", "официальный", "сайт",
     "минута", "ru", "купить", "выгодная", "отзыв", "цена",
     "представить", "через", "широкий", "удобный",
     "интернет", "магазин", "россия", ]
)


morph = MorphAnalyzer()


class PromoML(ABC):
    @abstractmethod
    def __init__(self):
        pass

    def clear_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^а-яёА-ЯЁ ]", " ", text)
        text = re.sub(r" [а-яёЁА-Я] ", " ", text)
        text = re.sub(r" +", " ", text)
        return text

    def morph_analyzer(self, text: str, allowed_grammems: tuple) -> list:
        words = []

        for word in text.split(' '):
            word = morph.parse(word)[0]
            if word.tag.POS not in allowed_grammems and \
                    len(word.normal_form) > 3:
                words.append(word.normal_form)

        return words


class HTMLShopsClassifier(PromoML):
    """Classifies any texts by known categories, returns string with category
    Examples:
        category: str = HTMLShopsClassifier("Детский магазин игрушек LEGO.").category
    """

    def __init__(self, text: str):
        self.text = text
        self.forbidden_grammems = ('NUMR', 'PREP', 'CONJ', 'PRCL', 'INTJ')

    @property
    def category(self) -> str:
        return self.classify()

    def _classifier_morph(self, text: str) -> list:
        words = []

        for word in text.split(' '):
            word = morph.parse(word)[0]

            if word.tag.POS not in self.forbidden_grammems and \
                    len(word.normal_form) > 3:

                words.append(word.normal_form)

        return words

    def classify(self) -> str:
        text = self.clear_text(self.text)
        text: str = ' '.join(self._classifier_morph(text))
        text = [text]  # count_vectorizer needs iterable

        if len(text[0]) < 20:
            return "Разное"

        with open(constants.count_vectorizer, 'rb') as f:
            count_vectorizer = pickle.load(f)

        X = count_vectorizer.transform(text)

        with open(constants.tf_idf_transformer, 'rb') as f:
            tf_idf_transformer = pickle.load(f)

        X = tf_idf_transformer.transform(X)

        with open(constants.classifier, 'rb') as f:
            clf = pickle.load(f)

        probabilities = clf.predict_proba(X)

        if amax(probabilities) < 0.4:
            category_name = "Разное"
        else:
            category_name = constants.categories[clf.predict(X)[0]]

        return category_name


class TagsGetter(PromoML):
    """Gets tags from any text and returns list[str]
    Examples:
        tags: list = TagsGetter("Лучший ресторан быстрой доставки.").tags
    """

    def __init__(self, text):
        self.text = text
        self.allowed_grammems = ('NOUN',)

    def _tags_morph(self, text: str) -> list:
        words = []

        for word in text.split(' '):
            word = morph.parse(word)[0]

            if word.tag.POS in self.allowed_grammems and \
                    len(word.normal_form) > 3:

                words.append(word.normal_form)

        return words

    @property
    def tags(self) -> list:
        description = self.clear_text(self.text)
        tags = self._tags_morph(description)
        tags = set(tags)
        tags = list(tags - no_needed_words4tags)
        return tags


class TextExtractor(PromoML):
    def __init__(self, text):
        self.text = text

    @property
    def promocode_expiration_date(self) -> 'datetime.datetime | None':
        morph_vocab = MorphVocab()
        dates_extractor = DatesExtractor(morph_vocab)

        now = datetime.datetime.now()
        expiration_date = list(dates_extractor(self.text))

        if not expiration_date:
            del morph_vocab
            del dates_extractor
            return None

        expiration_date = expiration_date[-1].fact  # make order by date

        if not expiration_date.month or not expiration_date.day:
            del morph_vocab
            del dates_extractor
            return None

        year = expiration_date.year or now.year
        month = expiration_date.month
        day = expiration_date.day

        del morph_vocab
        del dates_extractor

        return datetime.datetime(year, month, day)

    @property
    def shop_name(self) -> str:
        navec = Navec.load(constants.navec_file)
        ner = NER.load(constants.ner_file)
        ner.navec(navec)

        try:
            markup = ner(self.text)
        except IndexError:
            # i dont know what happens here sometimes
            del navec
            del ner
            return ""

        for span in markup.spans:
            if span.type == 'ORG':
                del navec
                del ner
                return self.text[span.start:span.stop].strip(".,;!:-–—/ ")

        del navec
        del ner

        return ""


if __name__ == '__main__':

    tags = TagsGetter("Лучший ресторан быстрой доставки в москве.").tags
    print(tags)

    t = HTMLShopsClassifier("Детский магазин игрушек LEGO. лучшее для детей.").category
    print(t)
