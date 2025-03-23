from logger import *
import re
import json
import os
import datetime
import time


g_proj_path = os.path.abspath(os.path.join(os.path.dirname(__file__), r"../"))


def get_abs_path(rel_path):
    return os.path.abspath(os.path.join(g_proj_path, rel_path))


def pretty_print_dict(dic, indent=4):
    print(json.dumps(dic, indent=indent))


def get_cur_time():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]


class TimeCounter:
    def __enter__(self):
        self.start = time.time()

    def __exit__(self, exc_type, exc_value, tb):
        self.end = time.time()
        print("cost time: " + str(self.end - self.start))

