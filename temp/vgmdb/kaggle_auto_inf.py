from auto_web import *
import pyperclip
from selenium.webdriver.common.keys import Keys
import ast
import time


class kaggle_vocal_check_inf:
    def __init__(self, cookie_dir, cache_dir, script_url, res = []):
        self.slnm_web = SlnmWeb(cookie_dir, cache_dir)
        self.cookie_dir = cookie_dir
        self.cache_dir = cache_dir
        self.script_url = script_url
        self.run_all_btn = None
        self.need_click_more_outputs = True
        self.res_save_file = os.path.join(cache_dir, "res.json")
        self.res_save_file_bak = os.path.join(cache_dir, "res_bak.json")
        self.total_num = 0

        if res:
            self.res = res
        else:
            self.init_res_from_cache()

        self.new_res = res
        self.cur_ok_num = len(res)
        self.torr = 0
        self.cur_frame = "default"
        self.is_first_dl = True

    def init_res_from_cache(self):
        if os.path.exists(self.res_save_file):
            with open(self.res_save_file, "r") as f:
                self.res = json.loads(f.read())
        elif os.path.exists(self.res_save_file_bak):
            with open(self.res_save_file_bak, "r") as f:
                self.res = json.loads(f.read())
        else:
            self.res = []

    def login(self):
        self.slnm_web.open_url("https://www.kaggle.com/")
        self.slnm_web.wait_element_dead_loop('//*[@id="root"]/div[1]/div[2]/button')

    def open_script(self):
        self.slnm_web.open_url(self.script_url)
        self.slnm_web.wait_element_dead_loop("iframe", by_type=By.TAG_NAME)

    def switch_to_notebook(self):
        if self.cur_frame == "notebook":
            return
        self.slnm_web.web.switch_to.frame(self.slnm_web.web.find_elements(By.TAG_NAME, "iframe")[0])
        self.cur_frame = "notebook"

    def switch_to_default(self):
        if self.cur_frame == "default":
            return
        self.slnm_web.web.switch_to.default_content()
        self.cur_frame = "default"

    @staticmethod
    def clear_lable(ele):
        ele.click()
        time.sleep(1)
        ele.clear()

    def prepare(self):
        self.run_all_btn = self.slnm_web.web.find_element(By.XPATH, '//button[@title="Run All"]')
        while self.run_all_btn.get_attribute("disabled") is not None:
            print("wait btn enable...")
            time.sleep(20)
            if self.run_all_btn.get_attribute("disabled") is not None:
                self.slnm_web.web.find_element(By.XPATH, '//button[@aria-label="More settings"]').click()
                time.sleep(3)
                self.slnm_web.web.find_element(By.XPATH, '//p[text()="Restart & Clear Cell Outputs"]').click()
                time.sleep(3)
        self.switch_to_notebook()
        while True:
            try:
                res_content_eles = self.slnm_web.web.find_elements(By.XPATH, '//div[contains(@class, "cm-content")]')
                if not res_content_eles:
                    raise ElementNotInteractableException
                res_content_ele = res_content_eles[0]
                self.clear_lable(res_content_ele)
                if res_content_ele.text:
                    print("clear text fail, retry...")
                    raise ElementNotInteractableException
                break
            except ElementNotInteractableException as e:
                print("wait loading...")
                time.sleep(10)
        pyperclip.copy("res = %s" % self.res)
        time.sleep(1)
        res_content_ele.send_keys(Keys.CONTROL,'v')
        time.sleep(1)
        self.switch_to_default()

    def get_total_song_num(self):
        while True:
            try:
                page_src = self.slnm_web.web.page_source
                self.total_num = int(re.search(r"(?<=total song num:  )\d+", page_src).group())
                print("total num: %d" % self.total_num)
                return
            except AttributeError as e:
                print("get total num fail, wait...")
                time.sleep(10)

    def start(self):
        self.switch_to_default()
        time.sleep(3)
        self.run_all_btn = self.slnm_web.web.find_element(By.XPATH, '//button[@title="Run All"]')
        self.run_all_btn.click()
        print("start running...")
        # time.sleep(600)
        time.sleep(120)
        self.switch_to_notebook()
        self.get_total_song_num()
        self.switch_to_default()

    def restert(self):
        reset_btn = self.slnm_web.web.find_elements(By.XPATH, '//button[@aria-label="Factory reset"]')[0]
        assert reset_btn.get_attribute("disabled") is None
        reset_btn.click()
        time.sleep(1)

    def get_show_more_lable(self):
        click_xpath = '//pre[text()="Show more outputs"]'
        find_res = self.slnm_web.web.find_elements(By.XPATH, click_xpath)
        if find_res:
            return find_res[0]
        return None
    
    def dl_res_json(self):
        if self.is_first_dl:
            arrow_right_eles = self.slnm_web.web.find_elements(By.XPATH, '//span[text()="arrow_right"]')
            assert len(arrow_right_eles) == 3
            arrow_right_eles[1].click()
            time.sleep(10)
            self.is_first_dl = False
        more_act_btn = self.slnm_web.web.find_element(By.XPATH, '//p[text()="res.json"]/../../../..//button[text()="more_vert"]')
        more_act_btn.click()
        #先备份
        if os.path.exists(self.res_save_file):
            shutil.move(self.res_save_file, self.res_save_file_bak + str(time.time()))

        time.sleep(10)
        res_json_dl_btn = self.slnm_web.web.find_element(By.XPATH, '//span[text()="cloud_download"]')
        res_json_dl_btn.click()
        time.sleep(3)

    def update_res(self):
        # 等待文件下载完成
        while True:
            try:
                with open(self.res_save_file, "r") as f:
                    self.new_res = json.loads(f.read())
                return
            except FileNotFoundError as e:
                print("wait res.json...")
                time.sleep(10)

    def try_click_more_outputs(self):
        if self.get_show_more_lable():
            while True:
                try:
                    label = self.get_show_more_lable()
                    label.click()
                    time.sleep(3)
                    if self.get_show_more_lable() is None:
                        break
                    else:
                        print("i clicked label, but fail?")
                except ElementClickInterceptedException as e:
                    pass
            print("show more outputs...")
            self.need_click_more_outputs = False

    def get_new_res(self):
        # self.switch_to_notebook()
        # page_src = self.slnm_web.web.page_source
        # # 如果找到show more，则点击一下
        # if self.need_click_more_outputs:
        #     self.try_click_more_outputs()
            
        # res_list = re.findall(r"(?<=res:\n)\[\[.*?\]\]", page_src)
        # if not res_list:
        #     assert 0, "no res_list"
        # self.new_res = ast.literal_eval(res_list[-1])

        # with open(self.res_save_file , "w", encoding="utf-8") as f:
        #     f.write(json.dumps(self.new_res))

        self.dl_res_json()
        self.update_res()

        assert len(self.new_res)>=self.cur_ok_num, f"{len(self.new_res)} < {self.cur_ok_num}"

        print("cur ok: ", len(self.new_res))

        # 每250首歌重启一次，防止内存漏完
        if len(self.new_res) - len(self.res) >= 250:
            raise ValueError

        if len(self.new_res) == self.total_num:
            print("task finished!!!")
            return True

        if len(self.new_res) == self.cur_ok_num:
            self.torr += 1
        else:
            self.torr = 0
        if self.torr>=10:
            raise ValueError
        
        self.cur_ok_num = len(self.new_res)
        return False

    def running(self):
        while True:
            time.sleep(60)
            try:
                can_finish = self.get_new_res()
            except ValueError as e:
                print("task not exists any more, return...")
                return False
            if can_finish:
                return True 

    def exit(self):
        self.slnm_web.web.quit()



# def start_vocal_check_inf_web(cookie_dir, script_url, res = []):
#     inf_web = SlnmWeb(cookie_dir)
#     inf_web.open_url("https://www.kaggle.com/")
#     inf_web.wait_element_dead_loop('//*[@id="root"]/div[1]/div[2]/button')
#     inf_web.open_url(script_url)
#     inf_web.wait_element("iframe", for_debug=True, by_type=By.TAG_NAME)
#     inf_web.web.switch_to.frame(inf_web.web.find_elements(By.TAG_NAME, "iframe")[0])
    
#     while True:
#         try:
#             res_content_eles = inf_web.web.find_elements(By.XPATH, '//div[contains(@class, "cm-content")]')
#             if not res_content_eles:
#                 raise ElementNotInteractableException
#             res_content_ele = res_content_eles[0]
#             res_content_ele.clear()
#             break
#         except ElementNotInteractableException as e:
#             print("wait loading...")
#             time.sleep(10)
#     pyperclip.copy("res = %s" % res)
#     res_content_ele.send_keys(Keys.CONTROL,'v')
    
#     # 切回原始页面，点击开始按钮
#     inf_web.web.switch_to.default_content()

#     run_all_btn = inf_web.web.find_element(By.XPATH, '//button[@title="Run All"]')

#     while run_all_btn.get_attribute("disabled") is not None:
#         print("wait btn enable...")
#         time.sleep(20)

#     run_all_btn.click()

#     print("run all ok")

#     time.sleep(600)
#     inf_web.web.switch_to.frame(inf_web.web.find_elements(By.TAG_NAME, "iframe")[0])

#     # 每10s获取一次刷新一次res，如果连续120s没有刷新，则认为出现异常。此时重启web。
#     need_click_more_outputs = True
#     cur_ok_num = len(res)
#     torr = 0

#     # 获取总的数量
#     page_src = inf_web.web.page_source
#     total_num = int(re.search(r"(?<=total song num:  )\d+", page_src).group())

#     # res存档
#     res_save_file = os.path.join(cookie_dir, "res.json")

#     print("start ok")

#     while True:
#         page_src = inf_web.web.page_source
#         # 如果找到show more，则点击一下
#         if need_click_more_outputs:
#             click_xpath = '//pre[text()="Show more outputs"]'
#             if inf_web.web.find_elements(By.XPATH, click_xpath):
#                 need_click_more_outputs = False
#                 inf_web.click(click_xpath)
        
#         res_list = re.findall(r"(?<=res:\n)\[\[.*?\]\]", page_src)
#         if not res_list:
#             assert 0, "no res_list"
#         new_res = ast.literal_eval(res_list[-1])
#         with open(res_save_file , "w", encoding="utf-8") as f:
#             f.write(json.dumps(new_res))

#         assert len(new_res)>=cur_ok_num, f"{len(new_res)} < {cur_ok_num}"

#         if len(new_res) == total_num:
#             print("task finished!!!")
#             return new_res, True

#         if len(new_res) == cur_ok_num:
#             torr += 1
#         else:
#             torr = 0
#         if torr>=10:
#             print("task not exists any more, return...")
#             return new_res, False
#         cur_ok_num = len(new_res)
#         time.sleep(10)


