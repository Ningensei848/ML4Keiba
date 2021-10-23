# -*- coding: utf-8 -*-

# Commented out IPython magic to ensure Python compatibility.

# # %cd "/content"
# !git clone https://github.com/Ningensei848/ML4Keiba.git

# !echo "Now, currrent directory is :"
# # %cd "/content/ML4Keiba"

# # !ls -la

import os
import re
import sys
import csv
import math
import json
import time
import random
import itertools
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
from concurrent.futures import ProcessPoolExecutor


import requests
from requests.exceptions import RequestException
from tqdm import tqdm

# !pip install line-bot-sdk;

GIT_AUTHOR_NAME = "Ningensei848-BOT"  # @param {type:"string"}
GITHUB_EMAIL = "bot@ningensei848.github.com"  # @param {type:"string"}
GITHUB_PERSONAL_ACCESS_TOKEN = os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN')

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

# 祖先の relationships を生成
parent = ['父', '母']
grandParent = [''.join(x) for x in itertools.product(parent, repeat=2)]
g1_grandParent = [''.join(x) for x in itertools.product(grandParent, parent)]
g2_grandParent = [''.join(x)
                  for x in itertools.product(g1_grandParent, parent)]
g3_grandParent = [''.join(x)
                  for x in itertools.product(g2_grandParent, parent)]
RELATIONSHIPS = [parent, grandParent,
                 g1_grandParent, g2_grandParent, g3_grandParent]

# 正規表現パターン
pattern_result_href = re.compile(r'/race/\d+')
pattern_horse_href = re.compile(r'/horse/\d+')

CATEGORY = ['sire', 'bms']

targets = []
BASE_DIR = Path.cwd().parent  # expected `/ML4Keiba`
DATA_ROOT = BASE_DIR / 'data'
DIR_CSV = DATA_ROOT / 'csv'
DIR_CSV_HORSE = DIR_CSV / 'horse'
# いったんはここに集積→溜まったら年別に振り分け
FILEPATH_INTERMEDIATE_HORSE = DIR_CSV / f'intermediate_horse.tsv'
DIR_CSV_SIRE = DIR_CSV_HORSE / 'sire'
targets.append(DIR_CSV_SIRE)

FILEPATH_INTERMEDIATE_SIRE = DIR_CSV_SIRE / 'intermediate_sire.tsv'
DIR_CSV_BMS = DIR_CSV_HORSE / 'bms'
targets.append(DIR_CSV_BMS)

FILEPATH_INTERMEDIATE_BMS = DIR_CSV_BMS / 'intermediate_bms.tsv'

DIR_LIST = DATA_ROOT / 'list'
DIR_LIST_HORSE = DIR_LIST / 'horse'
DIR_LIST_HORSE_FOREIGN = DIR_LIST_HORSE / 'foreign'
targets.append(DIR_LIST_HORSE_FOREIGN)

for dir in targets:
    dir.mkdir(parents=True, exist_ok=True)


def fetch(suffix):

    url = f'https://db.netkeiba.com/horse/{suffix}'
    response = requests.get(url)
    return response.content


def wait():
    time.sleep(random.uniform(1.5, 3))

# cf. https://kuroyagikun.com/python-line-message-picture-send/


def Notify2LINE(message, *args):
    # 諸々の設定
    line_notify_api = 'https://notify-api.line.me/api/notify'
    line_notify_token = os.environ.get('LINE_TOKEN')
    headers = {'Authorization': 'Bearer ' + line_notify_token}

    # メッセージ
    payload = {'message': message}
    requests.post(line_notify_api, data=payload, headers=headers)


def IsStallion(soup, horse_id):

    temp = soup.find_all(href=re.compile(f'horse/sire/{horse_id}'))

    if len(temp):
        return True
    else:
        return False

# getHorseProfile('000a00033a')  # 繁殖牡馬 stallion なので True
# getHorseProfile('1993109154')  # 牝馬 mare なので False
# getHorseProfile('2016102396')  # 牡馬だが sire になっていない


def isProcessed(horse_id):
    # csv を探ってすでに処理されているかどうか検証する関数

    # 外国産馬であれば，list に追加されているかどうか
    # 国内産馬であれば，intermediate_horse.tsv >> YYYY.tsv に追加されているか

    horse_id = str(horse_id)

    # prefix = horse_id[:4] if horse_id.isdecimal() else horse_id[3:7]
    filepath = DIR_LIST_HORSE / f'{horse_id[:4]}.txt' if horse_id.isdecimal(
    ) else DIR_LIST_HORSE_FOREIGN / f'{horse_id[3:7]}.txt'

    # 国産馬の場合
    if horse_id.isdecimal():
        if FILEPATH_INTERMEDIATE_HORSE.exists():
            # FILEPATH_INTERMEDIATE_HORSE を tsv として開く
            df = pd.read_csv(FILEPATH_INTERMEDIATE_HORSE,
                             index_col=0, delimiter='\t')

            if int(horse_id) in df.index:
                return True
        # ----------------------------------------------------------------------
        filepath = DIR_CSV_HORSE / f'{horse_id[:4]}.tsv'
        if filepath.exists():
            # DIR_CSV_HORSE/YYYY.tsv を tsv として開く
            df = pd.read_csv(filepath, index_col=0, delimiter='\t')

            if int(horse_id) in df.index:
                return True
    # 外国産馬の場合
    else:
        filepath = DIR_LIST_HORSE_FOREIGN / \
            f'{horse_id[3:7]}.txt'  # list なので拡張子は .txt でよい

        if not filepath.exists():
            return False
        elif horse_id in filepath.read_text().split('\n'):
            return True

    return False  # boolean


# hoge = isProcessed('2016102396')
# print('2016102396'.isdecimal())
# print(hoge)

def getHorseProfile(horse_id):
    """
    arg: horse_id
    return {
        horse_id: horse_id
        stallion: Boolean
        生年月日 :  YYYY-MM-DD
        調教師 :  trainerName
        馬主 :  OwnerName
        生産者 :  BreaderName
        産地 :  Place
        セリ取引価格 :  int
        獲得賞金 :  int
        通算成績 :  A-B-C-D (ABCD はいずれもint)
    }
    """
    html_doc = fetch(horse_id)
    soup = BeautifulSoup(html_doc, 'lxml')

    if soup is None:
        return

    db_prof_table = soup.find('table', attrs={'class': 'db_prof_table'})

    if db_prof_table is None:
        return

    # 不要なキーのリスト
    wasted_keys = ['募集情報', '主な勝鞍', '近親馬']

    # table から th を key として / td を value として取り出し，辞書形式に変換
    profile = {
        'horse_id': horse_id,
        # 繁殖種牡馬か判定　→　True なら getHorseSire を実行する
        'stallion': IsStallion(soup, horse_id)
    }

    # 前処理：余分な情報を消去して horse_id だけ残す
    result = db_prof_table.find('a', title='全競走成績').text

    for td in db_prof_table.find_all('td'):
        if td.a is None:
            continue
        else:
            id_ = td.a['href'].split('/')[2]
            td.string = id_

    temp = {tr.th.text: tr.td.text.strip() for tr in db_prof_table.find_all(
        'tr') if tr.th.text not in wasted_keys}
    profile.update(temp)

    # 凡例 -------------------------------------------------------------------------
    # 生年月日 :  2016年3月6日  # ハイフンに変更→　2016-03-06
    # 調教師 :  斉藤崇史 (栗東)  # 所属を削除　→　斉藤崇史
    # 馬主 :  サンデーレーシング
    # 募集情報 :  1口:35万円/40口  # 不要なので削除
    # 生産者 :  ノーザンファーム
    # 産地 :  安平町
    # セリ取引価格 :  -
    # 獲得賞金 :  8億7,342万円 (中央) # カッコ書きを削除し，数値に変換　→　873420000
    # 通算成績 :  14戦7勝 [7-3-3-1] # ハイフン表記だけ残す　→　7-3-3-1
    # 主な勝鞍 :  20'有馬記念(G1)  # 不要なので削除
    # 近親馬 :  ノームコア、ハピネスダンサー # 不要なので削除
    # ------------------------------------------------------------------------------

    # birthday ---------------------------------------------------------------------
    if '生年月日' in profile:
        m_birthday = re.match('\d+年\d+月\d+日', profile['生年月日'])
        m_birthyear = re.match('\d+年', profile['生年月日'])
        if m_birthday:
            birthday = datetime.strptime(profile['生年月日'], '%Y年%m月%d日')
            profile['生年月日'] = str(birthday.date())
        elif m_birthyear:
            profile['生年月日'] = profile['生年月日'][:-1]
        else:
            profile['生年月日'] = ''

    # trainer ----------------------------------------------------------------------
    if '調教師' in profile:
        profile['調教師'] = re.sub('\s*[（\(].*?[）\)]$', '', profile['調教師'])

    # sale price -------------------------------------------------------------------
    if 'セリ取引価格' in profile:
        m_price = re.match(r'(.*)万円', profile['セリ取引価格'])
        if not m_price:
            pass  # セリ無しの場合
        else:
            price = re.sub('\D', '', m_price.group(1))
            profile['セリ取引価格'] = int(price + '0000')  # XX 万円

    # career prize money -----------------------------------------------------------
    if '獲得賞金' in profile:
        m_prize = re.match(r'(.*)万円', profile['獲得賞金'])
        if not m_prize:
            pass  # 獲得賞金無しの場合
        else:
            prize = re.sub('\D', '', m_prize.group(1))
            profile['獲得賞金'] = int(prize + '0000')  # XX 万円

    # career stats -----------------------------------------------------------------
    if '通算成績' in profile:
        profile['通算成績'] = result

    # ------------------------------------------------------------------------------

    # for confirmination --------
    # for k, v in profile.items():
    #     print(k, ': ', v)
    # ---------------------------

    return profile


# getHorseProfile('2010100157')
# getHorseProfile(2016104750)

def getHorseResult(horse_id):
    """
    arg: horse_id
    return {
        race_history: str
    }
    """
    html_doc = fetch(f'result/{horse_id}')
    soup = BeautifulSoup(html_doc, 'lxml')

    if soup is None:
        return

    db_prof_table = soup.find('table', attrs={'class': 'db_h_race_results'})

    if db_prof_table is None:
        return {'race_history': ''}

    # race_id には int 以外も含まれるので str 型にすること　＝＞　e.g. 2021J0032708　
    race_id_list = [a['href'].split(
        '/')[2] for a in db_prof_table.find_all(href=pattern_result_href)]

    return {
        # 順番を並び替えて返して（昇順になおす），`-->` で結合
        'race_history': '-->'.join(race_id_list[::-1])
    }


# getHorseResult(2016104750)
# getHorseResult('000a00033a')

def getHorsePedigree(horse_id):
    """
    arg: horse_id
    return ped (dict)
    """
    html_doc = fetch(f'ped/{horse_id}')
    soup = BeautifulSoup(html_doc, 'lxml')

    if soup is None:
        return

    db_prof_table = soup.find('table', attrs={'class': 'blood_table'})

    if db_prof_table is None:
        print(horse_id, file=sys.stderr)
        return

    # 前処理：余分な情報を消去して horse_id だけ残す
    for td in db_prof_table.find_all('td'):
        if td.a is None:
            td.string = '-'
            continue
        else:
            horse_id = td.a['href'].split('/')[2]
            td.string = horse_id

    dfs = pd.read_html(db_prof_table.prettify())
    df = dfs[0]

    ped = {}

    for gen in range(5):
        temp = df[gen].tolist()
        # range(start, stop, step)
        ancestor = [temp[i] for i in range(0, len(temp), 2 ** (4 - gen))]
        for r, id_ in zip(RELATIONSHIPS[gen], ancestor):
            ped[r] = id_

    return ped


# getHorsePedigree(2016104750)
# getHorsePedigree('000a00111c')

# getHorsePedigree('000a015743')

# getHorsePedigree(1998101516)

def columnFix(col):
    if col[0] == col[1]:
        return ''.join(col[0].split())
    else:
        return f'{col[0]}/{col[1]}'


def getHorseSire(horse_id):
    """
    arg: horse_id
    return dict
    """
    # sire と mare がある
    # 牡馬 には sire / blood mare sire のランキングがある
    # 牝馬には mare ランキングがある
    html_doc = fetch(f'sire/{horse_id}')
    # 馬名ではなく，horse_id に置き換えたい
    soup = BeautifulSoup(html_doc, 'lxml')

    if soup is None:
        return

    for tag in soup.find_all(href=pattern_horse_href):
        tag.string = tag['href'].split('/')[2]  # horse_id

    try:
        dfs = pd.read_html(soup.prettify())
    except ValueError as ve:
        # print(ve, file=sys.stderr)
        # print('Hint: comfirm your `horse_id`; Is it mare horse ?', file=sys.stderr)
        return {}

    result = {}

    for df, cat in zip(dfs, CATEGORY):
        df = df.drop(index=0)  # 「累計」成績を削除　←　後から合計して算出すればいいため
        # カラム名を取得して処理（今回の場合，特殊な二段組になっているため）
        # columns = [ '/'.join(list(set(col))[::-1]) for col in df.columns ]
        # columns = [ s.replace(' ', '') for s in columns ]
        try:
            columns = [columnFix(col) for col in df.columns]
        except Exception as e:
            print(f'[Error happend!!] df.columns is {df.columns}')
            columns = [columnFix(col)
                       for col in df.columns if type(col) is not int]
        # for debug ----------
        # for col in columns:
        #     print(col)
        # -------------------

        # horse_idをカラムおよび実データに挿入
        columns.insert(0, 'horse_id')
        df.insert(0, 'horse_id', horse_id)

        table = df.values.tolist()
        table.insert(0, columns)
        result[cat] = table

    return result


# result = getHorseSire('2010105827')
# result = getHorseSire('000a00033a')
# result = getHorseSire('1993109154')
# result = getHorseSire('000a015743')

# for debug --------------------------------------------------------------------
# for k,v in result.items():
#     print(k, ': ', v)
# ------------------------------------------------------------------------------

def processHorseData(horse_id):

    data = {}

    profile = getHorseProfile(horse_id)

    if profile is None:
        return

    wait()
    data.update(profile)
    del profile

    ped = getHorsePedigree(horse_id)

    if ped is None:
        return

    wait()
    data.update(ped)
    del ped

    race = getHorseResult(horse_id)

    if race is None:
        return

    wait()
    data.update(race)
    del race

    if 'stallion' in data and data['stallion'] is True:
        sire = getHorseSire(horse_id)

        if sire is None:
            return

        wait()
        data.update(sire)
        del sire

    return data


# for debug --------------------------------------------
# horse_id = '000a00033a'  # サンデーサイレンス
# horse_id = 2016104750  # クロノジェネシス
# horse_id = '000a015743' # D'Arcy's Yellow Turk
# horse_id = '2010100157'  # ジーマにジック

# profile = processHorseData(horse_id)

# for k,v in profile.items():
#     print(k, ':', v)
# ------------------------------------------------------

def updateHorseList(horse_id):

    horse_id = str(horse_id)

    filepath = DIR_LIST_HORSE / f'{horse_id[:4]}.txt' if horse_id.isdecimal(
    ) else DIR_LIST_HORSE_FOREIGN / f'{horse_id[3:7]}.txt'

    if filepath.exists():
        id_list = filepath.read_text(encoding='utf-8').split('\n')
    else:
        id_list = []

    if horse_id in id_list:
        return
    else:
        # horse_id が存在しなかった場合
        # 空白要素を削除
        id_list = [id_ for id_ in id_list if id_ != '']
        id_list.append(horse_id)

        with filepath.open(mode='w', encoding='utf-8') as f:
            f.write('\n'.join(id_list) + '\n')  # 末尾に改行文字を足す


# ------------------------------------------------

# updateHorseList('1993109154')
# updateHorseList('000a015743')
# updateHorseList('000a00033a')
# updateHorseList('000a0004c2')

def updateSireDataset(sire):

    rows = []

    if FILEPATH_INTERMEDIATE_SIRE.exists():
        rows = sire[1:]  # ヘッダ無し
    else:
        rows = sire  # ヘッダ有り

    with FILEPATH_INTERMEDIATE_SIRE.open(mode='a', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerows(rows)


def updateBloodMareSireDataset(bms):

    rows = []

    if FILEPATH_INTERMEDIATE_BMS.exists():
        rows = bms[1:]  # ヘッダ無し
    else:
        rows = bms  # ヘッダ有り

    with FILEPATH_INTERMEDIATE_BMS.open(mode='a', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerows(rows)


def updateMyDataset(profile):

    # horse_id を list に追加 -------------------------------------------
    updateHorseList(profile['horse_id'])

    # horse sire and bms ------------------------------------------------
    sire = profile.pop('sire', None)
    bms = profile.pop('bms', None)

    if sire is None:
        pass
    else:
        updateSireDataset(sire)

    if bms is None:
        pass
    else:
        updateBloodMareSireDataset(bms)

    # horse profile ------------------------------------------------------
    columns, rows = list(profile.keys()), list(profile.values())

    if FILEPATH_INTERMEDIATE_HORSE.exists():
        # ヘッダ無し
        with FILEPATH_INTERMEDIATE_HORSE.open(mode='a', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(rows)
    else:
        # ヘッダ有り
        with FILEPATH_INTERMEDIATE_HORSE.open(mode='a', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(columns)
            writer.writerow(rows)

# for debug

# horse_id = 2016102396
# horse_id = 1993109154
# horse_id = '000a00033a'


# if isProcessed(horse_id):
#     print('Already completed.')
# else:
#     profile = processHorseData(horse_id)
#     updateMyDataset(profile)

def trackAncestor(horse_id, generation, retry_count=1):

    # 世代が4以上前，あるいはすでに処理済みである場合はスキップ
    if generation > 4 or isProcessed(horse_id):
        return

    try:
        profile = processHorseData(horse_id)
    except RequestException as re:
        retry_count += 1
        if retry_count > 48:  # １日待っても接続が確立しない場合
            raise Exception(
                f'{retry_count * 1800 // 3600}時間待ちましたが，うまく接続できません；；\nエラー内容は以下のとおりです：\n\n{re}')
        else:
            Notify2LINE(
                f'【Warning】Connection Error ! retry {retry_count} times ...')
            time.sleep(1800)  # 30分待機
            trackAncestor(horse_id, generation, retry_count)  # 再度挑戦
            return

    # profile がうまく取れなかった場合，処理をスキップ
    if profile is None:
        return

    updateMyDataset(profile)
    parents = (profile['父'], profile['母'])
    id_list = [id_ for id_ in parents if id_ != '-']

    # 父も母も不明('-') であれば終了
    if len(id_list) == 0:
        return

    generation += 1

    for id_ in id_list:
        # recursive function
        trackAncestor(id_, generation)

    # with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
    #     executor.submit(fn=trackAncestor, horse_id=id_, generation=generation)


def childProcess(source):

    # data/csv/horse/sire/intermediate_sire.tsv または intermediate_bms.tsv
    # => horse_id が同一のもので取り出してから，初年度ごとに振り分け
    #     - data/csv/horse/sire/{YYYY}.tsv
    # source = DIR_CSV_SIRE / 'intermediate_sire.tsv'

    if not source.exists():
        return

    # -----------------------------------------------------------------
    sieve_dict = {}
    df = pd.read_csv(source, delimiter='\t')
    # horse_id ごとの df を取得して初年度産駒が出た年ごとに振り分け ---
    for horse_id in set(df['horse_id'].tolist()):
        # 特定の `horse_id` を持つ行だけ取り出す
        df_chunk = df[df['horse_id'].isin([horse_id])]
        firstCropYear = df_chunk[df_chunk.columns[1]].min(skipna=True)
        if firstCropYear not in sieve_dict:
            sieve_dict[firstCropYear] = df_chunk
        else:
            # 縦方向に連結
            sieve_dict[firstCropYear] = pd.concat(
                [sieve_dict[firstCropYear], df_chunk], axis=0)
    del df
    # -----------------------------------------------------------------
    # tsv ファイルとして出力 ------------------------------------------
    parent_dir = source.parent
    for year, df in sieve_dict.items():
        filepath = parent_dir / f'{year}.tsv'
        # データが有れば，それを読み込んで連結し，再度ファイルに出力
        if filepath.exists():
            # 縦方向に連結
            df_concat = pd.concat(
                [pd.read_csv(filepath, delimiter='\t'), df], axis=0)
            df_result = df_concat.drop_duplicates(subset=df.columns[:2])
            df_result.to_csv(filepath, sep='\t', index=False)
        else:
            # データがなければ，そのままファイルに出力
            df.to_csv(filepath, sep='\t', index=False)
    # -----------------------------------------------------------------
    # 最後に，中間ファイルを削除 -------------------------------------
    # try:
    #     source.unlink()
    # except:
    #     pass
    # ----------------------------------------------------------------


def prettifyDataset():

    # data/csv/intermediate_horse.tsv
    # => 各行を生年月日ごとに振り分け
    #     - data/csv/horse/{YYYY}.tsv
    source = DIR_CSV / 'intermediate_horse.tsv'
    sieve_dict = {}
    if source.exists():
        df = pd.read_csv(source, delimiter='\t', dtype='object')
        columns = df.columns
        # 生年月日ごとに振り分けて辞書を作る ----------------------------
        for _, series in df.iterrows():
            row = series.tolist()

            # True になっている部分は欠損値（NaN）なのでスキップ
            row_bool = series.isnull()
            if row_bool[0] or row_bool[2] or row[0] == 'nan':
                continue

            birthYear = row[2][:4] if len(row[2]) > 3 else 'YYYY'  # 生年月日
            if birthYear not in sieve_dict:
                sieve_dict[birthYear] = [row]
            else:
                sieve_dict[birthYear].append(row)
        del df
        # ----------------------------------------------------------------
        # tsv ファイルとして出力 -----------------------------------------
        for year, rows in sieve_dict.items():
            filepath = DIR_CSV_HORSE / f'{year}.tsv'

            # データが有れば，それを読み込んで連結し，再度ファイルに出力
            if filepath.exists():
                df = pd.read_csv(filepath, delimiter='\t', dtype='object')
                new_df = pd.DataFrame(rows, columns=columns)
                # 縦方向に連結
                df_concat = pd.concat([df, new_df], axis=0)
                df_result = df_concat.drop_duplicates(subset=df.columns[0])
                df_result.to_csv(filepath, sep='\t', index=False)
            else:
                # データがなければ，そのままファイルに出力
                df = pd.DataFrame(rows, columns=columns)
                df.to_csv(filepath, sep='\t', index=False)
        # ----------------------------------------------------------------
        # 最後に，中間ファイルを削除 -------------------------------------
        try:
            source.unlink()
        except:
            pass
        # ----------------------------------------------------------------

    # sire, bms については別の関数にて処理
    childProcess(DIR_CSV_SIRE / 'intermediate_sire.tsv')
    childProcess(DIR_CSV_BMS / 'intermediate_bms.tsv')


def makeCommands():
    dt = datetime.now(timezone(timedelta(hours=9))
                      ).strftime('%Y-%m-%d %H:%M:%S')
    git_pull = ['git', 'pull']
    git_add = ['git', 'add', '.']
    git_commit = ['git', 'commit', '-m', f'add: tsv files {dt}']
    git_gc = ['git', 'gc', '--prune=all']
    git_push = ['git', 'push']

    return [
        git_pull,
        git_add,
        git_commit,
        git_gc,
        git_push
    ]


childProcess(DIR_CSV_SIRE / 'intermediate_sire.tsv')