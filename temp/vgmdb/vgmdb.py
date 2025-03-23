import json
import re
from common import *
from web import *
import os
import random
from music_web import QQMusic, NEMusic
import difflib
from selenium.common.exceptions import *



# 截止2023，vgmdb共有专辑132718

def remove_brace(s):
    return re.sub(r"(\(.*?\)|\[.*?\]|（.*?）)", "", s)

def remove_space(s):
    return re.sub(r"\s|\(|\)|\[|\]|\t|\r|\n|～|~|·|・|!|「|」|『|』|？|\?", "", s)

def fuzz_cmp_str(s1, s2):
    # 去掉括号里的东西
    s1 = remove_space(remove_brace(s1)).lower()
    s2 = remove_space(remove_brace(s2)).lower()
    if s1 == s2:
        return 1
    if (s1 in s2) or (s2 in s1):
        return 0.95
    return difflib.SequenceMatcher(None, s1, s2).quick_ratio()

class VgmdbAlbumInfo:
    def __init__(self, album_dir):
        self.bc_session = BcSession()
        self.page = str()
        self.page_tree = None
        self.url = str()
        self.cover_save_dir = "./cover/"
        self.meta_save_dir = "./meta/"
        self.album_save_dir = album_dir
        self.meta_cache = set()
        self.cur_album_id = -1
        self.album_info = dict()
        self.album_cache = set()
        self.album_url_set = set()      # 存放所有已经找到的专辑url，防止出现重复
        self.init_inner()
        self.cur_album_sch_point = 0
        self.dl_last_sleep_time = 0

    def init_inner(self):
        os.makedirs(self.cover_save_dir, exist_ok=True)
        os.makedirs(self.meta_save_dir, exist_ok=True)
        os.makedirs(self.album_save_dir, exist_ok=True)

        # 初始化元数据
        html_list = os.listdir(self.meta_save_dir)
        album_list = os.listdir(self.album_save_dir)
        for html in html_list:
            album_id = int(html.split(".")[0])
            # todo: 打开校验
            # assert str(album_id) + ".json" in json_list
            self.meta_cache.add(album_id)

        for album in album_list:
            idx = int(album.split(".")[0])
            self.album_cache.add(idx)
            abm_info = self.get_album_info_from_local(idx)
            if abm_info:
                self.album_url_set.add(abm_info["url"])

        logger.info("find %d html is ok" % (len(html_list),))
        logger.info("find %d album is ok" % (len(album_list),))

        self.init_cur_album_info()

    def init_cur_album_info(self):
        self.album_info = dict()
        self.album_info["basic"] = dict()
        self.album_info["credits"] = dict()
        self.album_info["tracklist"] = dict()
        self.album_info["notes"] = str()
        self.album_info["name"] = {"en": "", "ja": "", "ja-Latn": ""}

    def set_point(self, num):
        self.cur_album_sch_point = num

    def dump_debug_info(self):
        print(self.album_info)

    def get_album_cover(self):
        cover_img_url = self.page_tree.xpath('//*[@id="coverart"]/@style')
        try:
            cover_img_url = cover_img_url[0]
            cover_img_url = re.search(r"(?<=url\(\').*(?=\'\))", cover_img_url).group()
        except Exception:
            logger.error("cannot find cover url: %s" % (cover_img_url,))
            exit(1)
        return cover_img_url

    def get_album_info(self):
        # 获取专辑标题
        for lang in self.album_info["name"].keys():
            for tr in self.page_tree.xpath('//*[@id="innermain"]/h1/span[@lang="%s"]/text()' % lang):
                self.album_info["name"][lang] = tr

        lang_list = []
        for li in self.page_tree.xpath('//*[@id="tlnav"]/li'):
            lang_list.append(li.xpath('./a/text()')[0])

        track_list_all_lang = []
        for span in self.page_tree.xpath('//*[@id="tracklist"]/span'):
            track_list = []
            for tr in span.xpath('.//tr[@class="rolebit"]'):
                track_list.append(tr.xpath('./td[2]/text()')[0].replace("\n", ""))
            track_list_all_lang.append(track_list)
        assert len(lang_list) == len(track_list_all_lang)

        for lang, tk in zip(lang_list, track_list_all_lang):
            self.album_info["tracklist"][lang] = tk

    def save_album_cover(self):
        cover_img_url = self.get_album_cover()
        # 下载封面
        img_format = cover_img_url.split(".")[-1]
        assert img_format in ["jpg", "jpeg", "png"], "invalid img_format, url: %s, album_id: %d, img_url: %s" % \
                                                     (self.url, self.cur_album_id, cover_img_url)
        self.bc_session.dl_img(cover_img_url, self.cover_save_dir + str(self.cur_album_id) + "." + img_format)

    def load_meta(self, album_id):
        self.url = "https://vgmdb.net/album/" + str(album_id)
        self.cur_album_id = album_id
        f = open('./meta/%d.html' % (album_id,), 'r', encoding='utf-8')
        self.page = f.read()
        f.close()
        self.page_tree = etree.HTML(self.page)

    def get_album(self, album_id):
        self.load_meta(album_id)
        # self.save_album_cover()   # todo: 打开
        self.get_album_info()
        if not self.album_info["tracklist"]:
            logger.error("album is not valid, id: %d, url: %s" % (album_id, self.url))
            assert ("An error has occurred!" in self.page) \
                   or ("This album was cancelled" in self.page) \
                   or ("No tracklist found" in self.page) \
                   or ("No official tracklist available" in self.page)
            return None
        return self.album_info

    def random_one_album_id(self):

        min_album_num = 1
        max_album_num = 33000

        mod = "no_randon"
        if mod == "randon":
            if len(self.meta_cache) > max_album_num * 0.98:
                logger.info("alg should change!")
                exit(1)
            while True:
                rand_id = random.randint(min_album_num, max_album_num)
                if rand_id not in self.meta_cache:
                    return rand_id
        else:
            for i in range(min_album_num, max_album_num):
                if i not in self.meta_cache:
                    return i

    def flow_ctrl_sleep(self):
        random_walk_step = random.randint(1, 100)
        step = random.randint(-random_walk_step, random_walk_step)
        self.dl_last_sleep_time = abs(self.dl_last_sleep_time + step)
        self.dl_last_sleep_time = min(self.dl_last_sleep_time, 100)
        sleep_time = self.dl_last_sleep_time / 10
        logger.info("sleep %d" % sleep_time)
        time.sleep(sleep_time)

    def dl_raw_page(self):
        while True:
            try:
                album_id = self.random_one_album_id()
                self.url = "https://vgmdb.net/album/" + str(album_id)
                logger.info("downloading url: %s" % (self.url,))
                self.bc_session.dl_html(self.url, self.meta_save_dir + str(album_id) + ".html")
                self.meta_cache.add(album_id)
                logger.info("download success! id: %d" % (album_id,))
                self.flow_ctrl_sleep()
            except Exception:
                logger.error("dl fail, wait 1m...")
                time.sleep(1 * 60)

    def get_best_match_idx(self, string, find_list):
        assert string and find_list
        idx = 0
        best_score = 0
        for i in range(len(find_list)):
            cur_score = fuzz_cmp_str(string, find_list[i])
            if cur_score == 1:
                return i, 1
            if cur_score > best_score:
                idx = i
                best_score = cur_score
        return idx, best_score

    def get_album_info_from_local(self, album_id):
        fp = os.path.join(self.album_save_dir, str(album_id)+".json")
        with open(fp, "r") as f:
            return json.loads(f.read())

    def save_album_info_to_local(self, album_id, data_w):
        fp = os.path.join(self.album_save_dir, str(album_id)+".json")
        with open(fp, "w") as f:
            f.write(json.dumps(data_w))
        logger.info("meta save ok, file: %s" % fp)

    def find_song_name_from_local(self, kwd):
        for i in range(1, self.cur_album_sch_point):
            try:
                local_album_info = self.get_album_info_from_local(i)
                if kwd in local_album_info["name"] or kwd in local_album_info["url"]:
                    print(i, local_album_info)
                    print(self.get_album(i))
            except (FileNotFoundError, KeyError) as e:
                continue


if __name__ == '__main__':
    pass
    # v = VgmdbAlbumInfo()
    # v.set_point(5000)
    # # v.get_album(2255)
    # # time.sleep(60*60*5)
    # # v.dl_raw_page()
    # # v.find_song_name_from_local("Secret Of Evermore")
    # # v.clear_local_album_info([882])
    # # exit(0)

    # while True:
    #     try:
    #         v.add_album_in_qq(1, 0, 200)
    #     except SessionNotCreatedException:
    #         logger.error("please upadte chrome driver from: "
    #                      "https://googlechromelabs.github.io/chrome-for-testing/#stable")
    #     except TimeoutException:
    #         continue


