
"""
TSVファイルの filepath を受け取る
df として読み込む

<< prefix なしで ttl に変換 >>

ttl に書き出しまでやって終了
"""

import os
import re
from pathlib import Path
import pandas as pd
import numpy as np
import itertools
import concurrent.futures

NaN = np.nan
pattern_id = re.compile(r'^\w{5,6}$')

parent = ['f', 'm']
grandParent = [''.join(x) for x in itertools.product(parent, repeat=2)]
g1_grandParent = [''.join(x) for x in itertools.product(grandParent, parent)]
g2_grandParent = [''.join(x)
                  for x in itertools.product(g1_grandParent, parent)]
g3_grandParent = [''.join(x)
                  for x in itertools.product(g2_grandParent, parent)]
RELATIONSHIPS = list(itertools.chain.from_iterable([
    parent, grandParent, g1_grandParent, g2_grandParent, g3_grandParent
]))

PREFIX = """
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix netkeiba: <https://db.netkeiba.com/> .
@prefix horse: <https://db.netkeiba.com/horse/> .
@prefix trainer: <https://db.netkeiba.com/trainer/> .
@prefix owner: <https://db.netkeiba.com/owner/> .
@prefix breeder: <https://db.netkeiba.com/breeder/> .

@prefix relation: <https://db.netkeiba.com/horse/ped#> .
@prefix race: <https://db.netkeiba.com/race/> .
@prefix baken: <https://db.netkeiba.com/race/baken/> .
"""


def renameColumns(df):
    df.rename(columns={
        '生年月日': 'birthday',
        '調教師': 'trainer',
        '馬主': 'owner',
        '生産者': 'breeder',
        '産地': 'country',
        'セリ取引価格': 'sale_price',
        '獲得賞金': 'prize_total',
    }, inplace=True)

    df.rename(columns=lambda s: s.replace('父', 'f').replace('母', 'm'),
              inplace=True)

    return df


def reformatDate(wrongDate):
    return '-'.join([x.zfill(2) for x in wrongDate.split('-')])


def processHorseDict(d):

    horseDict = {}
    for horse_id, row in d.items():
        win, second, third, lose = map(int, row['通算成績'].split('-'))
        tempDict = {
            'win': win,
            'second': second,
            'third': third,
            'lose': lose,
            'race_total':  win + second + third + lose
        }
        tempDict.update(row)
        del tempDict['通算成績']
        horseDict[horse_id] = tempDict

    return horseDict


def getRelation(row):

    lines = [
        ' '.join([f'\trelation:{rel}', f'horse:{row[rel]}' if row[rel] is not np.nan else '\"Unknown\"', ";"]) for rel in RELATIONSHIPS
    ]
    return '\n'.join(lines)


def getRaceHistory(row):
    if type(row['race_history']) is float:
        return '\thorse:race_history ()'

    races = [f'race:{race_id}' for race_id in row['race_history'].split('-->')]

    return f'\thorse:race_history ( {" ".join(races)} )'


def template(horse_id, row):
    birthday = f'\"{row["birthday"]}\"^^xsd:{"year" if len(row["birthday"]) == 4 else "date"}'
    trainer = '\"Unknown\"' if row['trainer'] is NaN or not pattern_id.match(str(row['trainer'])) \
        else f'trainer:{row["trainer"].zfill(5)}'
    owner = '\"Unknown\"' if row['owner'] is NaN or not pattern_id.match(str(row['owner'])) \
        else f'owner:{row["owner"].zfill(6)}'
    breeder = '\"Unknown\"' if row['breeder'] is NaN or not pattern_id.match(str(row['breeder'])) \
        else f'breeder:{row["breeder"].zfill(6)}'

    sale_price = f'\"{row["sale_price"]}\"^^xsd:nonNegativeInteger' if row["sale_price"] != '-' else f'\"{row["sale_price"]}\"'

    return '\n'.join([
        f"horse:{horse_id} horse:stallion {row['stallion']} ;",  # boolean
        f"\thorse:birthday {reformatDate(birthday)} ;",
        f"\thorse:trainer {trainer} ;",
        f"\thorse:owner {owner} ;",
        f"\thorse:breeder {breeder} ;",
        f"\thorse:country \"{row['country']}\" ;",  # xsd:string
        f"\thorse:sale_price {sale_price} ;",
        f"\thorse:prize_total \"{row['prize_total']}\"^^xsd:nonNegativeInteger ;",
        f"\thorse:win \"{row['win']}\"^^xsd:nonNegativeInteger ;",
        f"\thorse:second \"{row['second']}\"^^xsd:nonNegativeInteger ;",
        f" \thorse:third \"{row['third']}\"^^xsd:nonNegativeInteger ;",
        f"\thorse:lose \"{row['lose']}\"^^xsd:nonNegativeInteger ;",
        f"\thorse:race_total \"{row['race_total']}\"^^xsd:nonNegativeInteger ;",
        getRelation(row),
        f"{getRaceHistory(row)} .\n"
    ])


def preprocessing(df):
    df.replace('True', 'true', inplace=True)
    df.replace('False', 'false', inplace=True)

    return df


def col2dict(row, columns):
    return {name: row[name] for name in columns}


def processHorse(filepath: Path):
    # csv の日本語を一部変換
    # 全体を文字列（str 型）として読み込む；ただし欠損値は float 型として扱われる
    df = renameColumns(pd.read_csv(
        filepath, sep='\t', header=0, index_col=0, dtype=str
    ))

    # df の前処理
    df = preprocessing(df)
    columns = df.columns

    # 一行ごとに処理する：ついでに残った「通算成績」もパースしておく
    # horseDict = processHorseDict({
    #     horse_id: {name: row[name] for name in df.columns} for horse_id, row in df.iterrows()
    # })

    with concurrent.futures.ThreadPoolExecutor(os.cpu_count() * 5) as executor:
        future_to_dict = {
            executor.submit(col2dict, row, columns): horse_id for horse_id, row in df.iterrows()
        }
        horseDict = processHorseDict({
            future_to_dict[future]: future.result() for future in concurrent.futures.as_completed(future_to_dict)
        })

    with concurrent.futures.ThreadPoolExecutor(os.cpu_count() * 5) as executor:
        future_to_list = [
            executor.submit(template, horse_id, row) for horse_id, row in horseDict.items()
        ]
        # raceDict を ttl 文字列に加工する
        ttl = '\n'.join([
            future.result() for future in concurrent.futures.as_completed(future_to_list)
        ])

    # # horseDict を ttl 文字列に加工する
    # ttl = '\n'.join([template(horse_id, row)
    #                  for horse_id, row in horseDict.items()])

    # 拡張子を ttl に変える＆＆ディレクトリを `turtle` 以下に変更してからファイルに書き出す
    outputPath = Path(
        # csv と一致したら turtle に変える
        *[path if path != 'csv' else 'turtle' for path in filepath.with_suffix('.ttl').parts]
    )
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    outputPath.unlink(missing_ok=True)
    # outputPath.write_text(f'{PREFIX}\n\n{ttl}', encoding='utf-8')
    outputPath.write_text(ttl, encoding='utf-8')  # 個別ファイルのPREFIXは省略
