import requests
from lxml import etree
from common import *
from lxml import etree
from requests.adapters import HTTPAdapter


g_clash_proxy_port = 7890


class BcSession:
    def __init__(self, proxy_port=g_clash_proxy_port, headers=None):
        self.session = requests.Session()
        self.init_session()
        self.req_dict = dict()
        self.init_req_dict(proxy_port, headers)
        self.rsp_code = 0
        self.page = str()
        self.url = str()

    def init_session(self):
        self.session.mount("http://", HTTPAdapter(max_retries=3))
        self.session.mount("https://", HTTPAdapter(max_retries=3))

    def init_req_dict(self, proxy_port, headers):
        if proxy_port:
            self.req_dict['proxies'] = {
                'http': f'http://127.0.0.1:{proxy_port}',
                'https': f'http://127.0.0.1:{proxy_port}'
            }
        if headers:
            self.req_dict['headers'] = headers
        self.req_dict["url"] = str()
        self.req_dict["timeout"] = (30, 30)  # (连接超时，读取超时)

    def _set_url(self, url):
        self.req_dict["url"] = url

    @staticmethod
    def std_url(url):
        if url[:4] != "http":
            url_new = "https://" + url
            logger.warning("url is not start with http, change it to: %s" % (url_new,))
            return url_new
        return url

    def get_page(self, url):
        self.url = self.std_url(url)
        self._set_url(self.url)
        try:
            response = self.session.get(**self.req_dict)
            response.encoding = response.apparent_encoding
            self.rsp_code = response.status_code
            if response.status_code != 200:
                logger.error("status_code is %d" % (response.status_code, ))
                return ""
            self.page = response.text
            return self.page
        except requests.exceptions.RequestException:
            logger.error("time out, url: %s" % (url,))
            return ""

    def get_page_etree(self, url):
        return etree.HTML(self.get_page(url))

    def dl_html(self, url, file_path):
        # text = self.get_page(url)
        # assert text
        # with open(file_path, "wb") as f:
        #     f.write(text)
        response = self.session.get(url)
        with open(file_path, "wb") as f:
            f.write(response.content)

    # 下载图片
    def dl_img(self, url, file_path):
        response = self.session.get(url)
        with open(file_path, "wb") as f:
            f.write(response.content)


if __name__ == '__main__':
    vgmdb_home = "https://vgmdb.net/"
    s = BcSession()
    page_text = s.get_page("https://www.bing.com/")
    print(page_text)
