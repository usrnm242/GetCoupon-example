class Ads:
    def __init__(self, image: str, website: str, priority: int = 0):
        self.imageLink = image
        self.websiteLink = website
        self.priority = priority

    def __eq__(self, other):
        return self.websiteLink == other.websiteLink and \
               self.imageLink == other.imageLink

    def __repr__(self):
        return f"imageLink: {self.imageLink}\n"\
               f"websiteLink: {self.websiteLink}\n"


class AdsInCategory:
    """just read-only from db"""
    def __init__(self, linked_section: int, ads: list = None):
        self.linkedSection = linked_section
        self.adsList = [] if ads is None else ads

    def append_ads(self, ads: Ads):
        if ads not in self.adsList:
            self.adsList.append(ads)

    def __eq__(self, other):
        return self.linkedSection == other.linkedSection and \
               self.adsList == other.adsList

    def __repr__(self):
        return f"self.linkedSection: {self.linkedSection}\n"\
               f"self.adsList: {str(self.adsList)}\n"
