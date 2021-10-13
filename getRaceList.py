
# import os
import re
# import sys
# import csv
# import math
# import json
import time
import random
import itertools
# import subprocess
# from statistics import mean, median
# from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
# from concurrent.futures import ProcessPoolExecutor


import requests
from tqdm import tqdm


def fetch(suffix):

    url = f'https://db.netkeiba.com/race/{suffix}'
    response = requests.get(url)
    return response.content


def wait():
    time.sleep(random.uniform(1.5, 3))

cwd = Path.cwd()
dir = cwd / 'data' / 'csv' / 'horse'

pattern_w = re.compile(r'^[a-zA-Z0-9]+$')

trainer_list = []
owner_list = []
breeder_list = []
race_list = []

for filepath in dir.glob('*.tsv'):
    df = pd.read_csv(filepath, index_col=0, delimiter='\t', dtype='str', encoding='utf-8')

    # 調教師, 馬主, 生産者, race_history
    trainer_list.append([ item for item in df['調教師'].dropna() if pattern_w.match(item) ])
    owner_list.append([ item for item in df['馬主'].dropna() if pattern_w.match(item) ])
    breeder_list.append([ item for item in df['生産者'].dropna() if pattern_w.match(item) ])

    temp = [ item.split('-->') for item in df['race_history'].dropna() ]
    race_list.append([ item for item in set(itertools.chain.from_iterable(temp)) if pattern_w.match(item) ])

# TODO: 分類して追記
trainer_list = sorted(list(set(itertools.chain.from_iterable(trainer_list))))
owner_list = sorted(list(set(itertools.chain.from_iterable(owner_list))))
breeder_list = sorted(list(set(itertools.chain.from_iterable(breeder_list))))
race_list = sorted(list(set(itertools.chain.from_iterable(race_list))))

# コースコードを収集
code_list = sorted(list({ race_id[4:6] for race_id in race_list }))
target_race = {}

gomi = []
for race_id in race_list:
    course_code = race_id[4:6]
    if course_code in gomi:
        continue
    else:
        target_race[course_code] = race_id
        gomi.append(course_code)



# コースコードを地名に変換する辞書を準備
pattern_race_smalltxt = re.compile(r'^.*回(.+?)\d日目')
code_dict = {}

for course_code, race_id in tqdm(target_race.items()):
    html_doc = fetch(race_id)
    soup = BeautifulSoup(html_doc, 'lxml')
    mainrace_data = soup.find('div', attrs={'class': 'mainrace_data'})
    smalltxt = mainrace_data.find('p', attrs={'class': 'smalltxt'}).text

    m = pattern_race_smalltxt.match(smalltxt)
    course_name = m.group(1) if m else 'Unknown'
    code_dict[course_code] = course_name.replace('(', '_').replace(')', '') # 名前に半角カッコが含まれるのを防ぐ
    # break
    wait()



# 競馬場コードの種別判定 => 地方・中央・海外
association = {}

for course, v in code_dict.items():
    # コードが数字のみであれば，日本の競馬
    if course.isdecimal():
        num = int(course)
        # コードが 01 - 10 であれば，JRA管轄の競馬場コード
        if num > 10:
            association[course] = 'NAR'
        # コードが 11 より大きければ, NAR管轄の競馬場コード
        else:
            association[course] = 'JRA'
    # コードが英数字混合であれば，海外の競馬
    else:
        association[course] = 'WORLD'

# 開催年代を収集
year_list = sorted(list({ race_id[:4] for race_id in race_list }))


# race_id を年代・コースコードに振り分け
race_dict = { year: {} for year in year_list}

for race_id in race_list:
    year, course_code = race_id[:4], race_id[4:6]
    if course_code not in race_dict[year]:
        race_dict[year][course_code] = [ race_id ]
    else:
        race_dict[year][course_code].append(race_id)


target = Path.cwd() / 'data' / 'list' / 'race'

# race_dict を回して１．ディレクトリの作成　２．ファイルを出力
for year, dic in race_dict.items():
    # 必要なディレクトリの作成
    yearDir = target / year
    yearDir.mkdir(parents=True, exist_ok=True)

    for course_code, id_list in dic.items():
        # 必要なディレクトリ・パスの作成
        parentDir = yearDir / association[course_code]
        parentDir.mkdir(parents=True, exist_ok=True)
        filepath = parentDir / f'{course_code}_{code_dict[course_code]}.txt'
        # もしあれば，既存データとの統合
        if filepath.exists():
            orginal_data = filepath.read_text(encoding='utf-8')
            org_id_list = orginal_data.split()
            id_list = org_id_list + id_list
            id_list = list({ race_id for race_id in id_list if len(race_id) == 12 })

        # 整理して書き出し準備
        data = '\n'.join(sorted(id_list))
        filepath.write_text(data, encoding='utf-8')
        continue

# --------------------------------------------------------------------------------------------
# 上記までで集めたレースのリストのうち，歯抜けになっている部分を補足する --------------------------
# CAUTION : dirctory of `WORLD` is not target
dir_list = [year / 'JRA' for year in target.iterdir() ]
dir_list.extend([year / 'NAR' for year in target.iterdir() ])

for dir in tqdm(dir_list):
    for p in dir.glob('*.txt'):

        id_list = [] # init

        # collect temp_dict ----------------------------------
        temp_dict = {}
        for race_id in p.read_text().split():
            if race_id[:10] in temp_dict:
                temp_dict[race_id[:10]].append(race_id[10:])
            else:
                temp_dict[race_id[:10]] = [ race_id[10:] ]
        # ----------------------------------------------------
        # after temp_dict collected ... ----------------------
        for k,v in temp_dict.items():
            v.sort()
            # レース数に抜けがあれば，それを補足する
            if int(v[-1]) != len(v):
                temp_dict[k] = [str(x).zfill(2) for x in range(1, int(v[-1]) + 1)]
        # ----------------------------------------------------
        # k, v を合成して id_list に追加 ---------------------
        for k,v in temp_dict.items():
            id_list.extend([ k + v_i for v_i in v ])
        # ----------------------------------------------------
        # 元ファイルに書き込む -------------------------------
        id_list.sort()
        p.write_text('\n'.join(id_list))
        # ----------------------------------------------------
