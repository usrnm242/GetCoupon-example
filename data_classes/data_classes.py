from datetime import datetime, timedelta
import constants
from re import search, sub


sales_patterns = (r"(?:[сС]кидк|[вВ]ыгод[ау]|[хХ]аляв[нао][рР]аспродаж)[^!.]*",
                  r"[1-9][0-9]? де?н[ьяей][^!.]*",
                  r"-? ?[1-9][0-9]? ?(?:%|процент)[^!.]*",
                  r"[бБ]есплатн.{1,2}\ [^!.]*",
                  r"\n(.*за -? ?\d{1,3}? ?\d{3,4} ?[р₽].*\s?)", )


class Promocode:
    def __init__(
            self,
            coupon,
            estimated_date,
            promoCodeDescription,
            addingDate=datetime.now(),
            **kwargs):

        self.coupon: str = coupon
        self.addingDate: datetime = addingDate
        self.estimatedDate: datetime = estimated_date or \
            self.addingDate + timedelta(days=constants.days_promocode_is_valid)
        self.promoCodeDescription: str = promoCodeDescription
        self.source = kwargs.get('source', '')

    @classmethod
    def parseCouponShortDescription(
        self,
        text: str,
        patterns: tuple = sales_patterns
    ) -> str:

        for pattern in patterns:
            match = search(pattern, text)

            if match:
                text = match[0].strip()

                for regexp, initial_form_word \
                        in constants.initial_form_words.items():

                    text = sub(regexp, initial_form_word, text)

                break

        return text

    def isPinned(self) -> bool:
        return self.addingDate > datetime.now()

    def __eq__(self, other):
        return self.coupon == other.coupon

    def __hash__(self):
        return hash(self.coupon)

    def __repr__(self):
        return f"\n\tPROMOCODE INFO:\n"\
               f"promocode: {self.coupon}\n"\
               f"addingDate: {self.addingDate}\n"\
               f"expirationDate: {self.estimatedDate}\n"\
               f"promoCodeDescription: {self.promoCodeDescription}\n"


class Shop:
    def __init__(
            self,
            name,
            shopDescription,
            shopShortDescription,
            websiteLink,
            priority=0,
            tags=None,
            imageLink="",
            previewImageLink="",
            placeholderColor="#ffffff"):

        self.name: str = str(name)[:50]
        self.shopDescription: str = str(shopDescription)
        self.shopShortDescription: str = str(shopShortDescription)
        self.priority: int = int(priority)

        self.websiteLink: str = str(websiteLink)
        self.imageLink: str = str(imageLink)
        self.previewImageLink: str = str(previewImageLink)
        self.placeholderColor: 'list or str' = placeholderColor

        self.tags = tags if tags else []

        self.promoCodes: 'list[Promocode]' = []

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def appendPromocode(self, promocode):
        self.promoCodes.append(promocode)

    def sortPromocodesByAddingDate(self):
        self.promoCodes.sort(key=lambda promo: promo.addingDate, reverse=True)

    def checkPriority(self):
        has_promocodes: bool = (len(self.promoCodes) != 0)
        if not has_promocodes:
            self.priority = constants.priorities['zero']
        elif self.priority == constants.priorities['zero']:
            self.priority = constants.priorities['default']

    def parseShortDescriptionByLastAddedPromo(self):
        if len(self.promoCodes) > 0:
            if self.promoCodes[0].isPinned() and len(self.promoCodes) > 1:
                # if coupon is pinned and we've got more
                text = self.promoCodes[1].promoCodeDescription
            else:
                text = self.promoCodes[0].promoCodeDescription

            self.shopShortDescription = \
                Promocode.parseCouponShortDescription(text)

    def __repr__(self):
        return "\n\tSHOP INFO:\n"\
               f"\nshop_name: {self.name}"\
               f"\nshop_description: {self.shopDescription}"\
               f"\nshop_short_description: {self.shopShortDescription}"\
               f"\nshop_url: {self.websiteLink}"\
               f"\ntags: {self.tags}\n"


class ShopCategory:
    def __init__(self, categoryName, priority: int = None):
        self.categoryName: str = categoryName
        self.shops: list[Shop] = []
        self.tags: list = constants.categories_tags.get(self.categoryName,
                                                        [self.categoryName])
        self.defaultImageLink: str = \
            f"{constants.server_addr}"\
            f"{constants.default_images.get(self.categoryName, constants.default_image)}"
        self.priority: int = priority or \
            constants.categories_priorities.get(categoryName, 1)

    def __hash__(self):
        return hash(self.categoryName)

    def appendShop(self, shop):
        self.shops.append(shop)

    def appendTags(self, new_tags):
        self.tags.extend(new_tags)

    def sortShopsByPriorityAndLastAddedPromo(self):
        # shop.promoCodes[0] is the last added promo
        def assert_key(shop):
            if len(shop.promoCodes) > 0:
                return (shop.priority, shop.promoCodes[0].addingDate)
            else:
                return (0, 0)

        self.shops.sort(key=assert_key, reverse=True)

    def __repr__(self):
        return f"\n\tCATEGORY INFO:\n"\
               f"\ncategoryName: {str(self.categoryName)}"\
               f"\ntags: {str(self.tags)}"\
               f"\nshops: {str(self.shops)}"\
               f"\ndefault img: {str(self.defaultImageLink)}"


if __name__ == '__main__':
    descr = Promocode.parseCouponShortDescription("сегодня скидка 146% на авито! Налетай!")
    print(descr)
