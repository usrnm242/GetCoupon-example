from user_agent import generate_user_agent
import requests
import re
from .parser_constants import domains


# TODO: maybe asyncio


class HTMLGetter:
    @classmethod
    def get_request(self, url: str):
        headers = {"User-Agent": generate_user_agent(device_type="desktop",
                                                     os=('mac', 'linux',)),
                   "Accept": "text/html,application/xhtml_xml,application/xml;"
                             "q=0.9,image/webp,*/*;q=0.8,",
                   "Accept-Language": "ru",
                   "Accept-Encoding": "gzip, deflate",
                   "Connection": "keep-alive"}

        try:
            req = requests.get(url,
                               headers=headers,
                               timeout=10,
                               allow_redirects=True)
            req.encoding = 'utf-8'

        except Exception as e:
            raise(e)

        return req

    @classmethod
    def get_domain(self, url: str) -> str:
        url = HTMLGetter.get_root_website(url)
        url = re.sub(r"https?://", "", url)
        return url

    @classmethod
    def get_root_website(self, url: str) -> str:
        for domain in domains:
            domain_end_index = url.find(domain)

            if domain_end_index != -1:  # if found
                domain_end_index += len(domain)
                break

        url = url[0:domain_end_index]

        url = url.replace("www.", "")
        url = url.replace("https://m.", "https://", 1)

        return url

    @classmethod
    def follow_redirect(self, url: str) -> (str, str):
        """returns tuple = (last_url, html)"""
        req = HTMLGetter.get_request(url)
        last_url = req.url
        page = req.text
        return last_url, page

    @classmethod
    def cut_utm_from_url(self, url: str) -> str:
        utm_pattern = r"[&?]((admitad|utm).*?)$"  # r"[&?](utm.*?)[\s]"
        url = re.sub(utm_pattern, "", url)
        return url
