import os
import time
import shutil
import json


# 原始音频路径
raw_music_root_path = r"E:\music\20250227"

# 识别为有vocal的音频存放路径
pos_music_save_path = r"E:\music\pos"

# 由于疏漏没有过模型的曲子，后续需要打包重新过模型
remain_music_path = r"E:\music\remains"

# 将qq音乐下载好的音乐全部打包，每个包原始音频大小不超过500M
max_zip_pack_size = (1<<31)

# 压缩文件临时路径
temp_root_path = r"E:\music\temp"
temp_music_path = r"E:\music\temp\music"

# 所有元数据
all_metas_file = r"E:\music\metas\all_metas.json"


def pack_music_zip_file():
    if os.path.exists(temp_root_path):
        shutil.rmtree(temp_root_path)
    os.mkdir(temp_root_path)
    os.mkdir(temp_music_path)
    cur_size = 0
    cur_fn = 0
    cur_zip_num = 0
    file_list = os.listdir(raw_music_root_path)

    # 计算每个包的大小（均衡策略）
    total_size = sum([os.stat(os.path.join(raw_music_root_path,f)).st_size for f in os.listdir(raw_music_root_path)])
    pack_num = total_size//max_zip_pack_size + 1

    true_pack_size = total_size/pack_num
    print("total/pack_num/size:", len(file_list), pack_num, true_pack_size)

    for i, file in enumerate(file_list):
        file_fullpath = os.path.join(raw_music_root_path, file)
        file_cp_fullpath = os.path.join(temp_music_path, file)
        cur_size += os.stat(file_fullpath).st_size
        cur_fn += 1
        shutil.copyfile(file_fullpath, file_cp_fullpath)
        if cur_size < true_pack_size and i != len(file_list)-1:
            continue
        cur_size = 0
        cur_fn = 0
        pack_name = "music_zip" + str(cur_zip_num)
        print("pack...", pack_name, i+1)
        shutil.make_archive(os.path.join(temp_root_path, pack_name), 'gztar', root_dir='.', base_dir=temp_music_path)
        print("pack OK!", pack_name)
        cur_zip_num+=1
        shutil.rmtree(temp_music_path)
        os.mkdir(temp_music_path)
        # 改名，防止kaggle解压后看到数据
        shutil.move(os.path.join(temp_root_path, pack_name)+".tar.gz", os.path.join(temp_root_path, pack_name))
    

def copy_remain_musics(res):
    
    cnt = 0
    res_fset = set([_[0] for _ in res])

    for file in os.listdir(raw_music_root_path):
        if file not in res_fset:
            shutil.copyfile(os.path.join(raw_music_root_path, file), os.path.join(remain_music_path, file))
            cnt += 1
    print("find %d files not in res" % cnt)

def add_demus_res_to_meta(demus_res_file):
    # 先备份元数据
    shutil.copyfile(all_metas_file, all_metas_file+"_"+str(time.time())+".json")
    all_metas = json.loads(open(all_metas_file, "r").read())
    # 阈值
    thre = 50
    
    with open(demus_res_file, 'r') as f:
        res = json.loads(f.read())
        print("res len: %d" % len(res))

    # 剩余未识别的曲子数量
    copy_remain_musics(res)

    # 将本轮的pos样本拷贝到单独路径下，并合入all_metas中，去除重复音乐
    for [file, song_id, ratio] in res:
        file = os.path.basename(file)
        is_new_song = True
        if file in all_metas:
            print("find duplicate song: %s" % file)
            for dup_song in all_metas[file]:
                if dup_song[0] == song_id:
                    print("find a same song id, so we drop it")
                    is_new_song = False
                    break
            else:
                print("cannot find a same song id, add to meta...")
                all_metas[file].append([song_id, ratio])
        else:
            all_metas[file] = [[song_id, ratio]]
        if ratio >= thre:
            continue
        if not is_new_song:
            continue
        shutil.copyfile(os.path.join(raw_music_root_path, file), os.path.join(pos_music_save_path, file))

    with open(all_metas_file, "w") as f:
        f.write(json.dumps(all_metas))


def add_empty_album_info(file):
    with open(file, "w") as f:
        f.write("{}")

if __name__ == "__main__":
    res_file = r"E:\music\kaggle_output\res1741051853.5208192.json"
    add_demus_res_to_meta(res_file)

    # pack_music_zip_file()

    # add_empty_album_info("../vgmdb/album/ne/5215.json")
