import re
import os, shutil
from urllib import parse
from selenium.webdriver import Chrome
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from common import *
import requests
import zipfile
import requests
import threading
from queue import Queue


DEFAULT_COOKIE_PATH = r"C:\Users\11527\AppData\Local\Google\Chrome\slnm_data"
DEFAULT_DOWNLOAD_PATH = r"C:\Users\11527\Downloads"

class SlnmWeb:
    def __init__(self, root_dir=DEFAULT_COOKIE_PATH, download_path=DEFAULT_DOWNLOAD_PATH):
        self.url = str()
        self.usr_cookie_path = root_dir
        self.usr_download_path = download_path
        self.option = ChromeOptions()
        self.init_web_option()
        self.web = Chrome(options=self.option)
        # self.web.minimize_window()

    def init_web_option(self):
        os.makedirs(self.usr_cookie_path, exist_ok=True)
        # self.option.add_argument('--headless')
        # self.option.add_argument('--no-sandbox')
        # self.option.add_argument("--disable-dev-shm-usage")
        self.option.add_argument(r"user-data-dir=%s" % (self.usr_cookie_path, ))
        self.option.add_argument(r"user-data-dir=%s" % (self.usr_cookie_path, ))

        prefs = {
            "download.default_directory": self.usr_download_path,
            "download.prompt_for_download": False,  # 禁用下载弹窗
        }
        self.option.add_experimental_option("prefs", prefs)


    def hold_on(self, tm=1000000):
        logger.info("holding on...")
        time.sleep(tm)

    def open_url(self, url):
        self.url = url
        self.web.get(url)

    def wait_element(self, xpath_s, for_debug=True, by_type=By.XPATH, tmout=20):
        try:
            WebDriverWait(self.web, tmout).until(
                EC.presence_of_element_located((by_type, xpath_s))
            )
            logger.debug("element load ok, xpath: %s" % xpath_s)
        except TimeoutException as e:
            logger.error("page load element fail in %d s, xpath: %s, url: %s" % (tmout, xpath_s, self.url))
            logger.error("================= error occur! =================")
            logger.error(":(")
            logger.error(":(")
            logger.error(":(")
            logger.error(":(")
            logger.error(":(")
            # self.web.quit()
            logger.error("this error cannot be repaired, just holding on, you can debug now")
            if for_debug:
                self.hold_on()
            raise TimeoutException("page load element fail in %d s, xpath: %s, url: %s" % (tmout, xpath_s, self.url))

    def wait_element_dead_loop(self, xpath_s, by_type=By.XPATH, tmout=20):
        while True:
            try:
                self.wait_element(xpath_s=xpath_s, for_debug=False, by_type=by_type, tmout=tmout)
                break
            except TimeoutException as e:
                pass

    def click(self, xpath_s):
        self.wait_element(xpath_s)
        self.web.find_element(By.XPATH, xpath_s).click()

    def switch_frame(self, frame_id, ele_type="id"):
        self.wait_element('//*[@%s="%s"]' % (ele_type, frame_id))
        self.web.switch_to.frame(frame_id)
        logger.info("switch to new frame ok")

    def get_xpath_search_res(self, xpath_s, sub_xpath_s, attrib):
        res = []
        for ele in self.web.find_elements(By.XPATH, xpath_s):
            if sub_xpath_s:
                ele = ele.find_element(By.XPATH, sub_xpath_s)
            if attrib == "text":
                res.append(ele.text)
            else:
                res.append(ele.get_attribute(attrib))
        return res
    
    def get_ele_text(self, xpath_s):
        self.wait_element(xpath_s)
        time.sleep(3)
        return self.web.find_element(By.XPATH, xpath_s).text

    def run_by_action_list(self, action_list):
        for action in action_list:
            [op_type, para] = action
            if op_type == "open":
                self.url = para
                self.web.get(para)
                continue
            elif op_type == "wait":
                self.wait_element(para)
                continue
            elif op_type == "wait_ex":
                try:
                    self.wait_element(para)
                except TimeoutException as e:
                    logger.error("try again later")
                    time.sleep(10)
                    return 2
                continue
            elif op_type == "sleep":
                time.sleep(para)
            elif op_type == "switch_frame":
                self.switch_frame(para)
            elif op_type == "find_text":
                if re.search(para, self.web.page_source):
                    logger.error("find %s in page!" % para)
                    return 1
            else:
                logger.error("invalid action, %s" % op_type)
                assert 0
        return 0
    
    @staticmethod
    def download_file(file_url, file_path, retry_time=3):
        for _ in range(retry_time):
            try:
                response = requests.get(file_url, stream=True)
                if response.status_code != 200:
                    print("download fail, response.status_code is %d" % response.status_code)
                    time.sleep(2)
                    continue
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                    return True
            except Exception as e:
                print("download fail: %s, %s" % (file_path, file_url))
                time.sleep(2)
        return False
    
    # 多线程下载
    def download_file_mt(self, file_urls, file_paths, thread_count=3, retry_time=3):
        def worker(queue):
            while not queue.empty():
                args = queue.get()
                self.download_file(**args)
                queue.task_done()

        task_queue = Queue()
        for file_url, file_path in zip(file_urls, file_paths):
            task_queue.put({"file_url":file_url, "file_path":file_path, "retry_time":retry_time})

        threads = []
        for _ in range(thread_count):
            thread = threading.Thread(target=worker, args=(task_queue,))
            thread.start()
            threads.append(thread)

        task_queue.join()
        for thread in threads:
            thread.join()


def update_chromedriver():
    requset = requests.get("https://googlechromelabs.github.io/chrome-for-testing/#stable")
    re_res = re.search(r"https://storage\.googleapis\.com/chrome-for-testing-public/[\d\.]+/win64/chromedriver-win64\.zip", str(requset.content))
    assert re_res
    url = re_res.group()

    chrome_driver_root = r"D:\Users\11527\anaconda3"
    temp_dir = os.getcwd()
    zip_file = os.path.join(temp_dir, "chromedriver-win64.zip")

    src_exe_file = os.path.join(temp_dir, r"chromedriver-win64\chromedriver.exe")
    dst_exe_file = os.path.join(chrome_driver_root, "chromedriver.exe")


    with open(zip_file, "wb+") as f:
        r = requests.get(url)
        f.write(r.content)
        f.close()

    zf = zipfile.ZipFile(zip_file)
    zf.extractall(temp_dir)

    shutil.copy2(src_exe_file, dst_exe_file)
    shutil.rmtree(os.path.join(temp_dir, r"chromedriver-win64"))


if __name__ == '__main__':
    update_chromedriver()