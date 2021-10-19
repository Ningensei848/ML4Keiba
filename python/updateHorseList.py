"""
data/csv/horse : 親の一覧を取ってくる
data/csv/race : 出走馬の一覧を取ってくる
"""

import re
import itertools
from typing import List, Dict, Set
from pathlib import Path
from tqdm import tqdm
import pandas as pd
import numpy as np


parent = ['父', '母']
grandParent = [''.join(x) for x in itertools.product(parent, repeat=2)]
g1_grandParent = [''.join(x) for x in itertools.product(grandParent, parent)]
g2_grandParent = [''.join(x)
                  for x in itertools.product(g1_grandParent, parent)]
g3_grandParent = [''.join(x)
                  for x in itertools.product(g2_grandParent, parent)]
RELATIONSHIPS = list(itertools.chain.from_iterable([
    parent, grandParent, g1_grandParent, g2_grandParent, g3_grandParent
]))

BASE_DIR = Path.cwd().parent  # /ML4Keiba
HORSE_DIR = BASE_DIR / 'data' / 'csv' / 'horse'
HORSE_LIST_DIR = BASE_DIR / 'data' / 'list' / 'horse'
HORSE_FILES = sorted(list(HORSE_DIR.glob('*.tsv')))

RACE_DIR = BASE_DIR / 'data' / 'csv' / 'race'
RACE_RESULT_FILES = sorted(list(RACE_DIR.glob('**/result/*.tsv')))

pattern_foreign_horse = re.compile(r'000a\w{6}|x000\w{6}')


def getDict(horse_list: List[str]) -> Dict[str, List[str]]:
    result_dict: Dict[str, List[str]] = {}
    # id の前4桁を取ってきて，国産馬判定→そうでなければ学国産馬
    for horse_id in horse_list:
        # 国産馬 --------------------------
        if horse_id[:4].isdecimal():
            if horse_id[:4] in result_dict and len(result_dict[horse_id[:4]]) > 0:
                result_dict[horse_id[:4]].append(horse_id[:10])
            else:
                result_dict[horse_id[:4]] = [horse_id[:10]]
        # 外国産馬 ------------------------
        else:
            # horse_id が 英数字 10 桁じゃない外国産馬は無視する
            if not pattern_foreign_horse.match(horse_id):
                continue
            if horse_id[3:7] in result_dict and len(result_dict[horse_id[3:7]]) > 0:
                result_dict[horse_id[3:7]].append(horse_id)
            else:
                result_dict[horse_id[3:7]] = [horse_id]

    return result_dict


def mergeHorseDict(d_org: Dict[str, List[str]], d_new: Dict[str, List[str]]):

    result_dict = {key: value for key, value in d_org.items()}

    for key, value in d_new.items():
        # 2つめの辞書のキーが，1つ目の辞書にもあるとき，マージしてやる
        if key in d_org:
            result_dict[key] = d_org[key] + value
        # 逆に，1つ目の辞書にはないとき，追加してやる
        else:
            result_dict[key] = value

    return result_dict


# 変数初期化
horse_dict: Dict[str, List[str]] = {}

# main01: 系統図情報をもとにした馬リスト
for filepath in tqdm(HORSE_FILES):

    # tsv を　df として読み込む
    df = pd.read_csv(filepath, sep='\t', header=0, index_col=0, dtype=str)
    # 父母…の列を取ってきて合成
    temp = list(itertools.chain.from_iterable(
        [df[rel].tolist() for rel in RELATIONSHIPS]
    ))

    horseIdSet: Set[str] = set([x for x in temp if x is not np.nan])

    horse_dict = mergeHorseDict(horse_dict, getDict(horseIdSet))

# main02: レース情報をもとにした馬リスト更新
for filepath in tqdm(RACE_RESULT_FILES):
    # tsv を　df として読み込む
    df = pd.read_csv(filepath, sep='\t', header=0, dtype=str)
    horseIdSet = set(
        [h for h in df['馬名'].tolist() if h is not np.nan and len(h) > 0]
    )
    horse_dict = mergeHorseDict(horse_dict, getDict(horseIdSet))


# 辞書の情報をもとに，情報をマージする
# data/list/horse/[id4].txt あるいは data/list/horse/foregin/[id4].txt をリストとして読み込む
# 情報をマージしてソート，その後書き込んで保存
for id4, horse_list in tqdm(horse_dict.items()):
    filepath = HORSE_LIST_DIR / f'{id4}.txt' if id4.isdecimal() \
        else HORSE_LIST_DIR / 'foreign' / f'{id4}.txt'
    # filepath が存在しない場合は，ファイルを作る
    if not filepath.exists():
        filepath.touch()
    # ファイルを読み込んで，改行で分割しリストを得る
    horse_list_org: List[str] = filepath.read_text(
        encoding='utf-8'
    ).split('\n')
    # 得られたリストを結合
    horse_list_org.extend(horse_list)
    # strip してソートして uniq する
    result = sorted(list(set([h.strip() for h in horse_list_org if len(h)])))
    # 書き込んで終了
    filepath.write_text('\n'.join(result)+'\n', encoding='utf-8')
