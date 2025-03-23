from auto_web import *
from vgmdb import *
from music_web import *
from urllib3.exceptions import *
import sys


vgmdb_cfg_list = [
    {
        "song_tb_url": "https://music.163.com/#/playlist?id=13377750783",
        "cookie_dir": r"C:\Users\11527\AppData\Local\Google\Chrome\slnm_data4",
        "cache_dir": r"E:\music\src\vgmdb\cache\vgmdb_4",
        "pos": [7400, 10000],
    },
    {
        "song_tb_url": "https://music.163.com/#/playlist?id=13447623195",
        "cookie_dir": r"C:\Users\11527\AppData\Local\Google\Chrome\slnm_data5",
        "cache_dir": r"E:\music\src\vgmdb\cache\vgmdb_5",
        "pos": [10000, 11000],
    },
]

vgmdb_cfg = vgmdb_cfg_list[int(sys.argv[1])]


mweb = NEMusic(vgmdb_cfg["song_tb_url"], vgmdb_cfg["cookie_dir"], vgmdb_cfg["cache_dir"])
mweb.open_home_and_wait()

# vgmdb_ins = VgmdbAlbumInfo("./album/qq/")
vgmdb_ins = VgmdbAlbumInfo("./album/ne/")

start_pos = vgmdb_cfg["pos"][0]
vgmdb_ins.set_point(vgmdb_cfg["pos"][1])


# 增加缓存，防止反复回滚
temp_cache_file = os.path.join(vgmdb_cfg["cache_dir"], "cache.json")

if not os.path.exists(temp_cache_file):
    with open(temp_cache_file, "w") as f:
        f.write("{}")


temp_cache = {}
with open(temp_cache_file, "r") as f:
    temp_cache = json.loads(f.read())

def find_i_th_album(i):
    global temp_cache

    if i in vgmdb_ins.album_cache:
        return

    # 加载当前专辑信息
    vgmdb_ins.init_cur_album_info()
    if vgmdb_ins.get_album(i) is None:
        return

    # 寻找专辑名匹配的专辑
    find_flag = False
    print("\n")
    print(f"meta: {i}.html")
    print(vgmdb_ins.album_info["name"])
    sch_name = ""
    album_url = ""
    match_score = 0
    vg_album_name_by_lang = list(vgmdb_ins.album_info["name"].items())

    # 优先尝试日语专辑名
    vg_album_name_by_lang.sort(key=lambda x: x[0] != "ja")
    for name_lang, album_name in vg_album_name_by_lang:
        # 罗马音如果和en相同，则跳过
        if name_lang != 'en' and album_name == vgmdb_ins.album_info["name"]["en"]:
            continue
        # 去除限定标识
        album_name = re.sub(r"\s*\[Limited Edition\]", "", album_name)
        album_cache = temp_cache.get(album_name, None)
        if album_cache is None:
            album_search_res = mweb.get_album_search_res(album_name)
            album_search_res = [[item[0], item[1], fuzz_cmp_str(album_name, item[0]), False]
                                for item in album_search_res]
            album_search_res.sort(key=lambda x: x[2], reverse=True)

            temp_cache[album_name] = album_search_res
            with open(temp_cache_file, "w") as f:
                f.write(json.dumps(temp_cache))
        else:
            logger.info("load from cache:")
            print(album_cache)
            album_search_res = album_cache

        logger.debug(f"sort result: {album_search_res}")

        # 如果非重名专辑太多，则只搜索前10个匹配专辑
        # 如果都是重名专辑，说明是烂大街的名字，此时只能一个个找
        search_album_temp_map = set()
        for res_id, item in enumerate(album_search_res):
            if res_id>0:
                # 设置上一个搜索记录为已检查。然后刷盘
                temp_cache[album_name][res_id-1][3] = True
                with open(temp_cache_file, "w") as f:
                    f.write(json.dumps(temp_cache))
            [sch_name, album_url, score, has_checked] = item
            search_album_temp_map.add(sch_name)

            if has_checked:
                continue

            logger.info(f"try match album {album_name},sch_res: {item}")

            if len(search_album_temp_map)>10:
                logger.warning("i have checked many times, i abandom")
                break

            if score < 0.6:
                logger.error(f"score is too low, skip it. album: {album_name}")
                continue
            sch_tk_list = mweb.get_song_list(album_url)
            # 遍历专辑名，优先找罗马音?
            all_track = vgmdb_ins.album_info["tracklist"]
            all_song_with_all_lang = [song for lang in all_track for song in all_track[lang]]
            for lang in all_track.keys():
                score_list = [vgmdb_ins.get_best_match_idx(song[0], all_song_with_all_lang)[1]
                                    for song in sch_tk_list]
                total_score = sum(score_list)
                high_rate_score = sum([score > 0.95 for score in score_list])

                # 长度少于一半，跳过
                if len(sch_tk_list) < len(all_track[lang])/2:
                    break
                # 精确匹配的数量至少要到30%
                if (len(sch_tk_list)>=5) and (high_rate_score < 0.3 * len(sch_tk_list)):
                    break
                
                # 防止单曲匹配
                if len(sch_tk_list) == 1:
                    acc = 0.95
                elif len(sch_tk_list) == 2:
                    acc = 0.9
                elif len(sch_tk_list) <= 4:
                    acc = 0.7
                else:
                    acc = 0.5

                if total_score > 0 and total_score >= acc * len(sch_tk_list):
                    logger.info("match success!score: %f, qq album name: %s, acc: %f" %
                                (total_score, sch_name, acc))
                    match_score = total_score * 100 / len(sch_tk_list)
                    find_flag = True
                    break
                else:
                    logger.info("match fail, score/lenth_s/t=(%f, %d, %d)" % (total_score, len(sch_tk_list), len(all_track[lang])))
                    # print(sch_tk_list)
                    # print(all_song_with_all_lang)
                    # print(score_list)
            if find_flag:
                break
        if find_flag:
            break

    data_w = dict()
    if find_flag:
        logger.info("find album ok, url: %s" % album_url)
        data_w = {"name": sch_name, "url": album_url, "s": sch_tk_list}
        time.sleep(3)
        if album_url in vgmdb_ins.album_url_set:
            logger.warning("url already in local cache, url: %s" % album_url)
        else:
            # 如果都是disable，则无需添加歌单
            if sum([(not song[2]) for song in sch_tk_list]) > 0:
                mweb.add_album_like()
            else:
                logger.warning("all song is disable, cannot add album like")
            vgmdb_ins.album_cache.add(i)
            vgmdb_ins.album_url_set.add(album_url)
    else:
        logger.error("can not find album")
        vgmdb_ins.dump_debug_info()

    temp_cache = {}
    with open(temp_cache_file, "w") as f:
        f.write(json.dumps(temp_cache))
    vgmdb_ins.save_album_info_to_local(i, data_w)


for i in range(start_pos, vgmdb_ins.cur_album_sch_point):
    while True:
        try:
            find_i_th_album(i)
            break
        except (TimeoutException, ReadTimeoutError) as e:
            continue
        except WebDriverException as e:
            del mweb
            mweb = NEMusic(vgmdb_cfg["song_tb_url"], vgmdb_cfg["cookie_dir"])
            mweb.open_home_and_wait()
            continue

