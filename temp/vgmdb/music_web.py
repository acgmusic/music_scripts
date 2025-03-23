import time
from urllib import parse
from selenium.common.exceptions import *
from common import *
from auto_web import *


class MusicWeb:
    def __init__(self, slnm_root_dir, dl_dir):
        self.slnm = SlnmWeb(root_dir=slnm_root_dir)
        self.home_url = None
        self.album_search_url_format = None
        self.frame_name = None
        self.xpath_login_cover = None
        self.xpath_playlist = None
        self.xpath_playlist_item_sub = None
        self.xpath_songlist = None
        self.xpath_songlist_item_sub = None
        self.xpath_add_like = None

        self.album_info = None
        self.init_xpath()
        self.init_dir(dl_dir)

    def init_dir(self, dl_dir):
        self.dl_dir = dl_dir
        self.dl_song_dir = os.path.join(self.dl_dir, "download")
        self.dl_song_tmp_dir = os.path.join(self.dl_dir, "temp_dl")
        self.dl_album_meta = os.path.join(self.dl_dir, "album_meta")

        os.makedirs(self.dl_dir, exist_ok=True)
        os.makedirs(self.dl_song_dir, exist_ok=True)
        os.makedirs(self.dl_song_tmp_dir, exist_ok=True)
        os.makedirs(self.dl_album_meta, exist_ok=True)

    def init_xpath(self):
        raise NotImplementedError("")

    def wait_login_ok(self):
        raise NotImplementedError("")

    def check_no_songlist(self):
        raise NotImplementedError("")

    @staticmethod
    def check_song_disable(song_label):
        raise NotImplementedError("")
        
    def search_album(self, album_name):
        assert self.album_search_url_format
        sch_url = self.album_search_url_format % parse.quote(album_name)
        self.slnm.open_url(sch_url)
    
    def search_album_and_wait(self, album_name):
        while True:
            self.search_album(album_name)
            self.wait_login_ok()
            if self.frame_name is not None:
                self.slnm.switch_frame(self.frame_name, "id")
            time.sleep(3)
            if self.check_no_songlist():
                return 1
            try:
                self.slnm.wait_element(self.xpath_playlist)
                break
            except TimeoutException as e:
                if self.check_no_songlist():
                    return 1
                logger.error("wait songlist fail, try again later")
                time.sleep(5)
                continue
        time.sleep(3)
        return 0
    
    def get_album_search_res(self, album_name):
        self.search_album_and_wait(album_name)
        sub_xpath = self.xpath_playlist_item_sub
        url_list = self.slnm.get_xpath_search_res(self.xpath_playlist, sub_xpath['url'][0], sub_xpath['url'][1])
        name_list = self.slnm.get_xpath_search_res(self.xpath_playlist, sub_xpath['name'][0], sub_xpath['name'][1])
        if not url_list:
            logger.error("find no result!, album name: %s" % album_name)
        assert len(url_list) == len(name_list)
        return [[name_list[i], url_list[i]] for i in range(len(name_list))]


    def get_song_list(self, album_url, need_download=False):
        """
        :param album_url:
        :return: song list of album
        """
        self.album_info = None
        self.slnm.open_url(album_url)
        self.wait_login_ok()
        if self.frame_name is not None:
            self.slnm.switch_frame(self.frame_name, "id")
        self.slnm.wait_element(self.xpath_songlist)
        time.sleep(3)
        sub_xpath = self.xpath_songlist_item_sub
        url_list = self.slnm.get_xpath_search_res(self.xpath_songlist, sub_xpath['url'][0], sub_xpath['url'][1])
        name_list = self.slnm.get_xpath_search_res(self.xpath_songlist, sub_xpath['name'][0], sub_xpath['name'][1])
        label_list = self.slnm.get_xpath_search_res(self.xpath_songlist, sub_xpath['label'][0], sub_xpath['label'][1])
        artist_list = self.slnm.get_xpath_search_res(self.xpath_songlist, sub_xpath['artist'][0], sub_xpath['artist'][1])
        if not url_list:
            logger.error("find no result!, album url: %s" % album_url)
        assert len(url_list) == len(name_list)

        songname_list = [artist + " - " + name for artist, name, label in zip(artist_list, name_list, label_list)]

        # songname_enable_list = [songname_list[i] for i in range(len(label_list)) if not label_list[i]]
        # url_enable_list = [url_list[i] for i in range(len(label_list)) if not label_list[i]]
        # song_dl_path_list = [os.path.join(self.dl_song_tmp_dir, songname) for songname in songname_enable_list]

        # # 暂时不支持，因为只有老专辑才能这么下载。
        # if need_download:
        #     shutil.rmtree(self.dl_song_tmp_dir)
        #     os.makedirs(self.dl_song_tmp_dir, exist_ok=True)
        #     self.slnm.download_file_mt(url_enable_list, song_dl_path_list)

        #     # 检查是否全部下载成功
        #     for file in os.listdir(self.dl_song_tmp_dir):
        #         src_file = os.path.join(self.dl_song_tmp_dir, file)
        #         dst_file = os.path.join(self.dl_song_dir, file)
        #         shutil.move(src_file, dst_file)

        self.album_info = [[songname_list[i], url_list[i], self.check_song_disable(label_list[i])] for i in range(len(name_list))]
        return self.album_info

    def open_home_and_wait(self, loop=True):
        self.slnm.open_url(self.home_url)
        if not loop:
            return
        while True:
            try:
                self.wait_login_ok()
                break
            except TimeoutException as e:
                logger.info("login fail, waiting...")
                continue
        logger.info("login ok")

    def add_album_like(self):
        raise NotImplementedError("")

class QQMusic(MusicWeb):
    def __init__(self, slnm_root_dir, dl_dir):
        super().__init__(slnm_root_dir, dl_dir)
        self.home_url = "https://y.qq.com"
        self.album_search_url_format = "https://y.qq.com/n/ryqq/search?w=%s&t=album&remoteplace=txt.yqq.center"
        
    def init_xpath(self):
        self.xpath_login_cover = '//*[@id="app"]//img[contains(@class, "top_login__cover")]'
        self.xpath_playlist = '//*[@id="app"]//ul[contains(@class, "playlist__list")]/li'
        self.xpath_playlist_item_sub = {
            'name': ['./h4/span/a/div', "title"],
            'url': ['./h4/span/a', "href"]
        }
        self.xpath_songlist = '//*[@id="app"]//ul[contains(@class, "songlist__list")]/li'
        self.xpath_songlist_item_sub = {
            'name': ['./div/div[@class="songlist__songname"]/span/a', "title"],
            'url': ['./div/div[@class="songlist__songname"]/span/a', "href"],
            'label': ['./div', "class"]
        }
        self.xpath_add_like = '//*[@id="app"]//i[contains(@class, "mod_btn__icon_like")]'

    def wait_login_ok(self):
        self.slnm.wait_element(self.xpath_login_cover, for_debug=False)

    def search_album(self, album_name):
        sch_url = "https://y.qq.com/n/ryqq/search?w=%s&t=album&remoteplace=txt.yqq.center" % parse.quote(album_name)
        self.slnm.web.get(sch_url)

    def check_no_songlist(self):
        check_no_songlist_kwd = "请检查输入的关键词是否有误或者过长"
        if re.search(check_no_songlist_kwd, self.slnm.web.page_source):
            logger.error("find %s in page!" % check_no_songlist_kwd)
            return True
        return False
    
    @staticmethod
    def check_song_disable(song_label):
        # 担心qq改变了disable歌曲的class标签。这里我们做严格的判断
        if song_label not in ['songlist__item', 
                         'songlist__item songlist__item--even', 
                         'songlist__item songlist__item--disable', 
                         'songlist__item songlist__item--even songlist__item--disable']:
            logger.error("invalid song lable: %s" % song_label)
            assert 0
        return "disable" in song_label

    def if_album_is_add_like(self):
        res = self.slnm.get_xpath_search_res('//*[@id="app"]//div[@class="data__actions"]/a[2]/span', '', "text")
        assert res and res[0] in ["收藏", "已收藏"], f"res not valid, {res}"
        return res[0] == "已收藏"

    def add_album_like(self):
        """ 先调用 get_song_list
        """
        if not self.if_album_is_add_like():
            self.slnm.click(self.xpath_add_like)
            # 检测是否添加成功
            time.sleep(2)
            add_like_retry_tm = 0
            while not self.if_album_is_add_like():
                time.sleep(1)
                logger.warning("try add like fail, waiting...")
                add_like_retry_tm += 1
                if add_like_retry_tm % 2 == 0:
                    self.slnm.click(self.xpath_add_like)
            logger.info("add like ok")
        else:
            logger.info("already add like")


class NEMusic(MusicWeb):
    def __init__(self, song_tb_urls, slnm_root_dir, dl_dir):
        super().__init__(slnm_root_dir, dl_dir)
        self.home_url = "https://music.163.com"
        self.album_search_url_format = "https://music.163.com/#/search/m/?s=%s&type=10"
        self.frame_name = "g_iframe"
        self.song_tb_cur_state = ""

        self.song_tb_name = "临时存放001"
        self.song_tb_url = song_tb_urls

        check_song_add_ok = True
        if check_song_add_ok:
            self.song_tb_cur_state = self.get_song_tb_cur_state(self.song_tb_url)

    def init_xpath(self):
        self.xpath_login_cover = '//*[@id="g-topbar"]//div[contains(@class, "m-tophead")]/div[1]/img'
        self.xpath_playlist = '//*[@id="m-search"]/div[2]/div/ul/li'
        self.xpath_playlist_item_sub = {
            'name': ['./div/a/span', "title"],
            'url': ['./div/a', "href"]
        }
        self.xpath_songlist = '//table[contains(@class, "m-table-album")]/tbody/tr'
        self.xpath_songlist_item_sub = {
            'name': ['./td[2]/div/div/div/span/a/b', "title"],
            'url': ['./td[2]/div/div/div/span/a', "href"],
            'label': ['.', "class"],
            'artist': ['./td[4]/div', "title"],
        }

    def wait_login_ok(self):
        self.slnm.wait_element(self.xpath_login_cover, for_debug=False)

    def check_no_songlist(self):
        try:
            album_num_str = self.slnm.get_ele_text('//*[@id="m-search"]/div[1]/em')
            album_num = int(album_num_str)
        except ValueError as e:
            logger.error("not a num: ", album_num_str)
            # todo: 这里暂时认为是因为加载慢了导致无法读取到页面上的专辑数量
            raise TimeoutException(e)
        if album_num == 0:
            logger.error("find 0 album in page!")
            return True
        return False
    
    @staticmethod
    def check_song_disable(song_label):
        if song_label not in ['even js-dis', ' js-dis', 'even ', ' ']:
            logger.error("invalid song lable: %s" % song_label)
            assert 0
        return "js-dis" in song_label
    
    def get_song_tb_cur_state(self, song_tb_url):
        self.slnm.web.get(song_tb_url)
        if self.frame_name is not None:
            self.slnm.switch_frame(self.frame_name, "id")
        xpath_s = '//div[@class="n-songtb"]/div[1]/span'
        self.slnm.wait_element(xpath_s)
        cur_state = self.slnm.web.find_element(By.XPATH, '//div[@class="n-songtb"]/div[1]/span').text
        logger.info("cur_state: %s" % cur_state)
        return cur_state
    
    def add_album_like(self):
        xpath_s = '//*[@id="content-operation"]/a[3]/i'
        self.slnm.wait_element(xpath_s)
        #如果是vip专辑，则需要点击a[1]
        if "收藏" not in self.slnm.web.find_element(By.XPATH, xpath_s).text:
            logger.info("its a vip album, text: %s" % self.slnm.web.find_element(By.XPATH, xpath_s).text)
            xpath_s = '//*[@id="content-operation"]/a[1]/i'
        while True:
            try:
                self.slnm.click(xpath_s)
                break
            except ElementClickInterceptedException as e:
                pass

        xpath_s = '//div[@class="zcnt"]/div[1]/div[2]/ul/li'
        try:
            self.slnm.wait_element(xpath_s, for_debug=False)
        except TimeoutException as e:
            # todo: fix me
            if "由于版权保护，您所在的地区暂时无法使用" in self.slnm.web.find_element(By.XPATH, '//div[@class="zcnt"]/div[1]/div[1]').text:
                logger.info("版权保护, add fail")
                return
            raise TimeoutException(e)
        for ele in self.slnm.web.find_elements(By.XPATH, xpath_s):
            if ele.find_element(By.XPATH, './div/p/a').text == self.song_tb_name:
                ele.click()
                break
        else:
            assert 0, "cannot find your song table: %s" % self.song_tb_name
        # 后续稳定后可以去除
        check_song_add_ok = True
        if check_song_add_ok:
            time.sleep(3)
            old_stat = self.song_tb_cur_state
            while True:
                self.song_tb_cur_state = self.get_song_tb_cur_state(self.song_tb_url)
                if old_stat != self.song_tb_cur_state:
                    break
                logger.error("add like fail, try again")
                self.slnm.open_url(self.home_url)


if __name__ == '__main__':
    song_tb_url = "https://music.163.com/#/playlist?id=13377750783"
    cookie_dir = r"C:\Users\11527\AppData\Local\Google\Chrome\slnm_data4"
    cache_dir = r"E:\music\src\vgmdb\cache\vgmdb_4"

    def test_slnmweb():
        web = SlnmWeb()
        web.open_url("https://y.qq.com/n/ryqq/search?w=&t=album&remoteplace=txt.yqq.center")
        web.run_by_action_list([])
        web.hold_on()

    def test_qq_login():
        qq_web = QQMusic()
        qq_web.open_home_and_wait()
        qq_web.slnm.hold_on()

    def test_qq_get_album_url():
        qq_web = QQMusic()
        qq_web.open_home_and_wait()
        res = qq_web.get_album_search_res("ゼルダの伝説 時のオカリナ リアレンジ・アルバム")
        print(res)
        qq_web.slnm.hold_on()


    def test_qq_get_album_song_list():
        qq_web = QQMusic()
        qq_web.open_home_and_wait()
        res = qq_web.get_song_list("https://y.qq.com/n/ryqq/albumDetail/001zwuxF01cmQG")
        print(res)
        qq_web.add_album_like()
        qq_web.slnm.hold_on()


    def test_ne_get_album_url():
        ne_web = NEMusic(song_tb_url, cookie_dir, cache_dir)
        ne_web.open_home_and_wait()
        res = ne_web.get_album_search_res("oath sign")
        print(res)
        ne_web.slnm.hold_on()


    def test_ne_get_album_song_list():
        ne_web = NEMusic(song_tb_url, cookie_dir, cache_dir)
        res = ne_web.get_song_list("https://music.163.com/album?id=37353454&uct2=U2FsdGVkX194DfVKbUoGjIMlf4vD8BSVktqJwxtGSkY=", True)
        print(res)
        ne_web.slnm.hold_on()


    test_ne_get_album_song_list()