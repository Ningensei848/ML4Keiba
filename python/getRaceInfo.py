
# # %cd "/content"
# !git clone https://github.com/Ningensei848/ML4Keiba.git

# !echo "Now, currrent directory is :"
# # %cd "/content/ML4Keiba"

# !ls -la

# !pip install line-bot-sdk;

import os
import re
import sys
# import csv
import math
# import json
import time
import random
import itertools
import subprocess
# from statistics import mean, median
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup


import requests
from tqdm import tqdm


# TODO: 00nan などの表記ゆれはなくす　
# cf. https://github.com/Ningensei848/ML4Keiba/blob/main/data/csv/race/1954/WORLD/result/A6_%E3%82%A4%E3%82%AE%E3%83%AA%E3%82%B9.tsv

GIT_AUTHOR_NAME = "Ningensei848-BOT"
GITHUB_EMAIL = "bot@ningensei848.github.com"
GITHUB_PERSONAL_ACCESS_TOKEN = os.environ.get(
    'GITHUB_PERSONAL_ACCESS_TOKEN', None)
LINE_ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN', None)

URL_WITH_ACCESS_TOKEN = f'https://{GIT_AUTHOR_NAME}:{GITHUB_PERSONAL_ACCESS_TOKEN}@github.com/Ningensei848/ML4Keiba.git'
local_config_username = ['git', 'config',
                         '--local', 'user.name', GIT_AUTHOR_NAME]
local_config_email = ['git', 'config', '--local', 'user.email', GITHUB_EMAIL]
remote_setUrl = ['git', 'remote', 'set-url', 'origin', URL_WITH_ACCESS_TOKEN]

procedure = [
    local_config_username,
    local_config_email,
    remote_setUrl
]

for proc in procedure:
    subprocess.run(proc, encoding='utf-8', stdout=subprocess.PIPE)


def fetch(suffix):

    url = f'https://db.netkeiba.com/race/{suffix}'
    response = requests.get(url)
    return response.content


def wait():
    time.sleep(random.uniform(1, 2))


def Notify2LINE(message, *args):
    # 諸々の設定
    line_notify_api = 'https://notify-api.line.me/api/notify'
    line_notify_token = LINE_ACCESS_TOKEN
    headers = {'Authorization': 'Bearer ' + line_notify_token}

    # メッセージ
    payload = {'message': message}
    requests.post(line_notify_api, data=payload, headers=headers)


# 1. レースのメタデータ

turf_type = ['芝', 'ダ', '障']
dir_type = ['右', '左', '直']
pattern_distance = re.compile(r'.+?(\d+)m')
pattern_title = re.compile(r'第\d+回')
pattern_grade = re.compile(r'[第\d+回]?(.+)\s*\((.+?)\)')
pattern_schedule = re.compile(r'(\d+)回(.*?)(\d+)日目')


def getRaceMetadata(soup, race_id):

    info_dict = {}

    if soup is None:
        return

    data = soup.find('div', attrs={'class': 'data_intro'})

    # コース種別，展開方向，距離，天候，地面の状態，発走時刻
    course_info = data.find('p').find('span').text
    temp = [x.strip() for x in course_info.split('/')]
    ground, weather, going, start_at = [x.split(' ' + ':') for x in temp]
    ground = ground[0]
    m_distance = pattern_distance.match(ground)
    info_dict['track'] = ground[0] if ground[0] in turf_type else None
    info_dict['direction'] = ground[1] if ground[1] in dir_type else None
    info_dict['distance'] = m_distance.group(1) if m_distance else None
    info_dict['weather'] = weather[1].strip() if len(
        weather) > 1 and len(weather[1]) > 0 else None
    info_dict['going'] = going[1].strip() if len(
        going) > 1 and len(going[1]) > 0 else None
    info_dict['start_at'] = start_at[1].strip() if len(
        start_at) > 1 and len(start_at[1]) > 0 else None

    # カッコ書きがあれば，その中身がグレード表示
    # 重賞の場合，prefix として「第XX回」という表示もつく（が不要なので消す）
    title = data.find('h1').text
    title = re.sub(r'第\d+回', '', title)
    m_title = pattern_grade.match(title)
    info_dict['title'] = m_title.group(
        1) if m_title else pattern_title.sub('', title)
    info_dict['grade'] = m_title.group(2) if m_title else None

    # YYYY年MM月DD日, Order, Place, Days, requirement, rules
    race_info = data.find('p', attrs={'class': 'smalltxt'}).text
    temp = race_info.split()
    m_schedule = pattern_schedule.match(temp[1])
    info_dict['date'] = temp[0].replace(
        '年', '-').replace('月', '-').replace('日', '')
    info_dict['round'] = m_schedule.group(1) if m_schedule else None
    info_dict['place'] = m_schedule.group(2) if m_schedule else None
    info_dict['days'] = m_schedule.group(3) if m_schedule else None
    info_dict['requirement'] = temp[2] if len(temp) > 2 else None
    info_dict['rule'] = temp[3] if len(temp) > 3 else None

    # for debug --------------------
    # for k,v in info_dict.items():
    #     print(f'{k}: {v}')
    # ------------------------------

    # DataFrame としてまとめる
    df = pd.DataFrame.from_dict(info_dict, orient='index').T
    df.rename(index={0: race_id}, inplace=True)

    return df


# for debug ----------------------------------
# race_id = 202101010101
# html_doc = fetch(race_id)
# soup = BeautifulSoup(html_doc, 'lxml')
# SOUP_METADATA = soup.find('div', attrs={'class': 'netkeiba_toprace_block'})
# # print(SOUP_METADATA.prettify())
# df = getRaceMetadata(SOUP_METADATA, race_id)
# df
# --------------------------------------------

# 2. レース結果
pattern_sex = re.compile(r'(\D+)(\d+)')
pattern_weight = re.compile(r'(\d+[\.\d+]?)\(([+-]?\d+)\)')
pattern_racetime = re.compile(r'(\d+)\D+(\d+)\D+(\d+)')
COLUMNS_RESULT = ['着順', '枠番', '馬番', '単勝', '人気', '馬名', 'sex', 'age',
                  'weight', 'gain', '斤量', 'タイム', '着差', '通過', '上り',
                  '騎手', '調教師', '馬主', '賞金(万円)']


def getRaceResult(soup, race_id):

    if soup is None:
        return

    # 前処理 -------------------------------------------------------------------
    # 0. 隠されているカラムを取り出す（前処理）
    _ = [snap.unwrap() for snap in soup.find_all('diary_snap_cut')]
    # 1. td を取り出し，a タグがあるか調べ，その href 属性から id を置換する
    for td in soup.find_all('td'):
        a = td.find('a')

        if not a:
            continue
        elif a.has_attr('href') and a.has_attr('title'):
            id_ = a.attrs['href'].split('/')[2]
            td.string = id_
    # --------------------------------------------------------------------------
    # 本処理: html から pandas でテーブルを抜き出して処理 ----------------------
    html = f'<html><head></head><body>{soup.prettify()}</body></html>'
    df = pd.read_html(html)[0]
    # カラム名に含まれる空白を削除
    df.columns = [''.join(col.split()) for col in df.columns]
    # 不要なカラムの削除
    df.drop(columns=['ﾀｲﾑ指数', '調教ﾀｲﾑ', '厩舎ｺﾒﾝﾄ', '備考'], inplace=True)
    # --------------------------------------------------------------------------

    # 着順に「同着」が含まれている場合，例外処理が面倒なのでスキップする -------
    if '同着' in df['着差'].tolist()[:4]:
        # 同着リストに追加？
        return
    # --------------------------------------------------------------------------

    # 性齢の分離表示 -----------------------------------------------------------
    seirei = []
    for cell in df['性齢']:
        m_sex = pattern_sex.match(cell)
        sex = m_sex.group(1) if m_sex else None
        age = m_sex.group(2) if m_sex else None
        seirei.append([sex, age])

    df_seirei = pd.DataFrame(seirei, columns=['sex', 'age'])
    df.drop(columns=['性齢'], inplace=True)
    # --------------------------------------------------------------------------

    # 騎手/調教師の５桁ゼロ埋め, 馬主の６桁ゼロ埋め ----------------------------
    # NaN は "-----" で埋める ------------------------------------------------
    df.fillna({'騎手': '-----', '調教師': '-----', '馬主': '-----'}, inplace=True)
    df['騎手'] = [str(jockey).zfill(5) for jockey in df['騎手']]
    df['調教師'] = [str(trainer).zfill(5) for trainer in df['調教師']]
    df['馬主'] = [str(owner).zfill(5) for owner in df['馬主']]
    # --------------------------------------------------------------------------

    # タイムを秒数で表示 -------------------------------------------------------
    times = []
    df.fillna({'タイム': 0}, inplace=True)

    for cell in df['タイム']:

        if cell == 0:
            times.append(None)
            continue

        m_racetime = pattern_racetime.match(cell)
        if not m_racetime:
            times.append(None)
        else:
            minute = float(m_racetime.group(1)) * 60
            sec = float(m_racetime.group(2))
            milisec = float(m_racetime.group(3)) / \
                (10 ** len(m_racetime.group(3)))
            times.append(minute + sec + milisec)

    df['タイム'] = times
    # --------------------------------------------------------------------------

    # 馬体重を体重と前回比に分離 -----------------------------------------------
    taiju = []
    for w in df['馬体重']:
        m_weight = pattern_weight.match(w)
        weight = m_weight.group(1) if m_weight else None
        gain = m_weight.group(2) if m_weight else None

        if weight is None:
            taiju.append([None, None])
        elif gain is None:
            taiju.append([weight, None])
        else:
            taiju.append([float(weight), float(gain)])

    df_taiju = pd.DataFrame(taiju, columns=['weight', 'gain'])
    df.drop(columns=['馬体重'], inplace=True)
    # --------------------------------------------------------------------------

    # 着差の１位の馬について，NaNを 0 に変換 -----------------------------------
    df.at[0, '着差'] = 0
    # --------------------------------------------------------------------------

    # 賞金の NaN を0に変換 -----------------------------------------------------
    df.fillna({'賞金(万円)': 0}, inplace=True)
    # --------------------------------------------------------------------------

    # df, df_seirei, df_taiju を結合 -------------------------------------------
    df_concat = pd.concat([df, df_seirei, df_taiju], axis=1)

    return df_concat.reindex(columns=COLUMNS_RESULT)

# for debug ----------------------------------
# race_id = 202101010101
# race_id = '2021J0032705'
# html_doc = fetch(race_id)
# soup = BeautifulSoup(html_doc, 'lxml')
# SOUP_RESULT = soup.find('table', attrs={'summary': 'レース結果'})
# # print(SOUP_RESULT.prettify())
# df = getRaceResult(SOUP_RESULT, race_id)
# df
# --------------------------------------------

# 3. 払い戻し


pattern_bar = re.compile(r'\s+-\s+')
pattern_arr = re.compile(r'\s+→\s+')

WIN_TABLE_LEFT = ['単勝:的中', '単勝:配当', '単勝:人気', '複勝_1:的中', '複勝_1:配当', '複勝_1:人気', '複勝_2:的中',
                  '複勝_2:配当', '複勝_2:人気', '複勝_3:的中', '複勝_3:配当', '複勝_3:人気', '枠連:的中', '枠連:配当',
                  '枠連:人気', '馬連:的中', '馬連:配当', '馬連:人気']
WIN_TABLE_RIGHT = ['ワイド_1:的中', 'ワイド_1:配当', 'ワイド_1:人気', 'ワイド_2:的中', 'ワイド_2:配当', 'ワイド_2:人気',
                   'ワイド_3:的中', 'ワイド_3:配当', 'ワイド_3:人気', '馬単:的中', '馬単:配当', '馬単:人気', '三連複:的 中',
                   '三連複:配当', '三連複:人気', '三連単:的中', '三連単:配当', '三連単:人気']
WIN_TABLE_ALL = WIN_TABLE_LEFT + WIN_TABLE_RIGHT


def makePaybackTable(df=None):

    if df is None:
        table = {k: None for k in WIN_TABLE_RIGHT}
        return pd.DataFrame.from_dict(table, orient='index').T

    table = {}

    for row in df.itertuples():
        _, name, win, divid, rank = row

        # `-` が含まれていれば，中間に挟まれている空白を削除
        win = pattern_bar.sub('-', win)
        win = pattern_arr.sub('=>', win)

        if name in ['複勝', 'ワイド']:
            for i, w, d, r in zip(range(1, 3+1), win.split(), divid.split(), rank.split()):
                table[f'{name}_{i}:的中'] = w
                table[f'{name}_{i}:配当'] = d
                table[f'{name}_{i}:人気'] = r
        else:
            table[f'{name}:的中'] = win
            table[f'{name}:配当'] = divid
            table[f'{name}:人気'] = rank

    return pd.DataFrame.from_dict(table, orient='index').T


def getPaybackTable(soup, race_id):

    if soup is None:
        return pd.DataFrame(index=[race_id], columns=WIN_TABLE_ALL)

    html = f'<html><head></head><body>{soup.prettify()}</body></html>'
    dfs = pd.read_html(html)

    # 一つしか見つからないときは，WIN_TABLE_LEFT だけ存在

    try:
        df_l = makePaybackTable(dfs[0])
        df_r = makePaybackTable() if len(
            dfs) == 1 else makePaybackTable(dfs[1])
    except AttributeError as ae:
        return pd.DataFrame(index=[race_id], columns=WIN_TABLE_ALL)

    # DataFrame としてまとめる
    df = pd.concat([df_l, df_r], axis=1)
    df.rename(index={0: race_id}, inplace=True)

    return df

# for debug --------------------------------------------------
# race_id = 202136010901
# html_doc = fetch(race_id)
# soup = BeautifulSoup(html_doc, 'lxml')
# SOUP_PAYBACK = soup.find('dl', attrs={'class': 'pay_block'})
# # print(SOUP_PAYBACK.prettify())
# df = getPaybackTable(SOUP_PAYBACK, race_id)
# df
# ------------------------------------------------------------

# 4. コーナー通過順位


def getSpacingOnCorner(soup, race_id):

    if soup is None:
        return pd.DataFrame(index=[race_id], columns=[f'spacing_on_corner:{i}' for i in range(1, 4+1)])

    html = f'<html><head></head><body>{soup.prettify()}</body></html>'

    dfs = pd.read_html(html, dtype=str)
    if len(dfs) == 0:
        return pd.DataFrame(index=[race_id], columns=[f'spacing_on_corner:{i}' for i in range(1, 4+1)])

    temp = {f'spacing_on_corner:{i}': None for i in range(1, 4+1)}

    for row in dfs[0].itertuples():
        col, val = row[1][:1], row[2]
        temp[f'spacing_on_corner:{col}'] = val

    # DataFrame としてまとめる
    df = pd.DataFrame.from_dict(temp, orient='index').T
    df.rename(index={0: race_id}, inplace=True)

    return df

# for debug -----------------------------------------
# race_id = 202101010101
# html_doc = fetch(race_id)
# soup = BeautifulSoup(html_doc, 'lxml')
# SOUP_CORNER = soup.find('table', attrs={'summary': 'コーナー通過順位'})
# # print(SOUP_CORNER.prettify())
# df = getSpacingOnCorner(SOUP_CORNER, race_id)
# df
# ---------------------------------------------------

# 5. ラップタイム


LAP_AND_PACE = ['laptime', 'pacemaker']


def getLapAndPace(soup, race_id):

    if soup is None:
        return pd.DataFrame(index=[race_id], columns=LAP_AND_PACE)

    html = f'<html><head></head><body>{soup.prettify()}</body></html>'
    dfs = pd.read_html(html, dtype=str)

    if len(dfs) == 0:
        return pd.DataFrame(index=[race_id], columns=LAP_AND_PACE)

    # init
    temp = {
        'ラップ': None,
        'ペース': None
    }
    temp = {row[1]: row[2] for row in dfs[0].itertuples()}

    # DataFrame としてまとめる
    df = pd.DataFrame.from_dict(temp, orient='index').T
    df.rename(index={0: race_id}, inplace=True)
    df.columns = LAP_AND_PACE

    return df


# for debug ----------------------------------
# race_id = 202103010101
# html_doc = fetch(race_id)
# soup = BeautifulSoup(html_doc, 'lxml')
# SOUP_LAPTIME = soup.find('table', attrs={'summary': 'ラップタイム'})
# # print(SOUP_LAPTIME.prettify())
# df = getLapAndPace(SOUP_LAPTIME, race_id)
# df
# --------------------------------------------

def getRaceDfs(race_id):

    race_id = str(race_id)
    html_doc = fetch(race_id)
    soup = BeautifulSoup(html_doc, 'lxml')

    # page 内の情報が（プレミアム）会員限定の場合，そのページの処理はスキップ
    if soup.find('p', attrs={'class': 'Premium_Regist_Msg'}):
        # print(soup.find('p', attrs={'class': 'Premium_Regist_Msg'}).prettify())
        return

    # 1. レースのメタデータ
    SOUP_METADATA = soup.find('div', attrs={'class': 'netkeiba_toprace_block'})
    df_metadata = getRaceMetadata(SOUP_METADATA, race_id)
    if df_metadata is None:
        return

    # 2. レース結果
    SOUP_RESULT = soup.find('table', attrs={'summary': 'レース結果'})
    df_result = getRaceResult(SOUP_RESULT, race_id)
    if df_result is None:
        return
    else:
        df_result['race_id'] = race_id

    # 3. 払い戻し
    SOUP_PAYBACK = soup.find('dl', attrs={'class': 'pay_block'})
    df_payback = getPaybackTable(SOUP_PAYBACK, race_id)

    # 4. コーナー通過順位
    SOUP_CORNER = soup.find('table', attrs={'summary': 'コーナー通過順位'})
    df_corner = getSpacingOnCorner(SOUP_CORNER, race_id)

    # 5. ラップタイム
    SOUP_LAPTIME = soup.find('table', attrs={'summary': 'ラップタイム'})
    df_laptime = getLapAndPace(SOUP_LAPTIME, race_id)

    df_concat = pd.concat(
        [df_metadata, df_payback, df_corner, df_laptime], axis=1)

    return df_result, df_concat

# for debug --------------------------------
# race_id = 202104030211
# df_result, df_concat = getRaceDfs(race_id)
# df_result
# df_concat
# ------------------------------------------


cwd = Path.cwd()
rootDir = cwd / 'data'
DIR_CSV = rootDir / 'csv'
DIR_CSV_RACE = DIR_CSV / 'race'


# 得られたDFをどのように出力するか？という問題
def mainProcess(race_id, result_path, stats_path):

    wait()
    try:
        dfs = getRaceDfs(race_id)
    except Exception as e:
        print(e, file=sys.stderr)
        print(f'Error occued! race_id is {race_id}', file=sys.stderr)
        p = cwd / 'error.log'
        with open(p, mode='a') as f:
            f.write(f'{race_id}\n')
        return

    if dfs is None:
        # race_id が dfs = Noneにしてしまうものを記録する
        p = cwd / 'none.log'
        with open(p, mode='a') as f:
            f.write(f'{race_id}\n')
        return

    result, stats = dfs[0], dfs[1]

    df_ex_result = pd.read_csv(
        result_path, delimiter='\t') if result_path.exists() else None
    df_ex_stats = pd.read_csv(stats_path, index_col=0,
                              delimiter='\t') if stats_path.exists() else None

    df_concat_result = pd.concat([df_ex_result, result])
    df_concat_stats = pd.concat([df_ex_stats, stats])

    df_concat_result.to_csv(
        result_path, encoding='utf-8', sep='\t', index=False)
    df_concat_stats.to_csv(stats_path, encoding='utf-8', sep='\t')

    return


def makeCommands():
    dt = datetime.now(timezone(timedelta(hours=9))
                      ).strftime('%Y-%m-%d %H:%M:%S')
    git_pull = ['git', 'pull', '--rebase', 'origin', 'main']
    git_add = ['git', 'add', '.']
    git_commit = ['git', 'commit', '-m', f'add: race info {dt}']
    git_gc = ['git', 'gc', '--prune=all']
    git_push = ['git', 'push']

    return [
        git_pull,
        git_add,
        git_commit,
        git_gc,
        git_push
    ]


DIR_LIST_RACE = rootDir / 'list' / 'race'


def main():

    for year in sorted([dir for dir in DIR_LIST_RACE.iterdir()], reverse=True):
        for dir in year.iterdir():
            for filepath in dir.glob('*.txt'):
                temp = DIR_CSV_RACE / '/'.join(filepath.parts[-3:-1])
                result_path = temp / 'result' / \
                    filepath.with_suffix('.tsv').name
                result_path.parent.mkdir(parents=True, exist_ok=True)
                stats_path = temp / 'stats' / filepath.with_suffix('.tsv').name
                stats_path.parent.mkdir(parents=True, exist_ok=True)

                collected_id_list = pd.read_csv(
                    stats_path, index_col=0, delimiter='\t').index if stats_path.exists() else []
                collected_id_list = [str(id_) for id_ in collected_id_list]

                for race_id in tqdm(filepath.read_text().split('\n')):
                    if race_id in collected_id_list:
                        continue
                    else:
                        mainProcess(race_id, result_path, stats_path)
            # ----------------------------------------------------------------------

            # after 1 directory completed ... --------------------------------------
            for proc in makeCommands():
                subprocess.run(proc, encoding='utf-8', stdout=subprocess.PIPE)
            # ----------------------------------------------------------------------

        # for debug ----------------------------------------------------------------
        #             break
        #         break
        #     break
        # break
        # --------------------------------------------------------------------------
    Notify2LINE(f'【Race scraping】{year.name}/ is completed!')
    # ------------------------------------------------------------------------------


for _ in range(2):
    main()
    subprocess.run(['python3', 'getRaceList.py'],
                   encoding='utf-8', stdout=subprocess.PIPE)
    time.sleep(3600 * 12)

Notify2LINE(f'【Race scraping】All Completed !!!!')
