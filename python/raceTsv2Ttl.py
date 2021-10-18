"""
data/csv/horse : 親の一覧を取ってくる
data/csv/race : 出走馬の一覧を取ってくる
"""

import re
import concurrent.futures
from typing import List
from pathlib import Path
import pandas as pd
import numpy as np


NaN = np.nan
Unknown = 'Unknown'
BAKEN = {
    '人気': 'baken:rank',
    '的中': 'baken:number',
    '配当': 'baken:dividend'
}
pattern_dividend = re.compile('|'.join(['配当'[::-1], '人気'[::-1], '的中'[::-1]]))
pattern_id = re.compile(r'\w{5,6}')

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


def reformatDate(wrongDate):
    return '-'.join([x.zfill(2) for x in wrongDate.split('-')])


def cornerRank(l: List[str]) -> str:
    return '( {elem} )'.format(elem=' '.join([f"\"{x}\"" for x in l]))


def isNumber(s):
    try:
        float(s)
    except ValueError:
        return False
    else:
        return True


def castDataForTtl(dic, key, datatype=None):
    return '\"Unknown\"' if dic[key] is NaN \
        else f'\"{dic[key]}\"^^{datatype}' if datatype is not None and isNumber(dic[key]) \
        else f'\"{dic[key]}\"'


def getDividends(row: pd.Series, cols: List[str]) -> str:

    dic = {}
    dividends = ''

    for col in sorted(cols):
        type_, cat = col.split(':')

        if type_ not in dic:
            dic[type_] = {cat: row[col]}
        else:
            dic[type_][cat] = row[col]

    # 辞書オブジェクトがつくれない，または単勝の記録さえない場合にはDividendの記載は無いものと判定
    if not len(dic) or dic['単勝']['配当'] is NaN:
        return ' '

    for type_, d in dic.items():
        if NaN in d.values():
            continue
        baken_type = type_ if '_' not in type_ else type_[:-2]
        baken = ' ;\n\t'.join(
            [f'\tbaken:type \"{baken_type}\"'] +
            [f'\t{BAKEN[cat]} \"{val}\"' for cat, val in d.items()]
        )
        dividends += f'\t[ {baken} ]\n '

    return f'\n{dividends}\t'


def getRunners(race_id, df) -> str:

    df_race = df[df['race_id'].isin([race_id])]
    columns = df.columns
    horseDict = {
        row['horse_id']: {col: row[col] for col in columns} for _, row in df_race.iterrows()
    }

    runners = ''

    for horse_id, dic in horseDict.items():
        finishing_order = castDataForTtl(
            dic, 'finishing_order', 'xsd:unsignedByte')
        post_position = castDataForTtl(
            dic, 'post_position', 'xsd:unsignedByte')
        horse_number = castDataForTtl(dic, 'horse_number', 'xsd:unsignedByte')
        odds = castDataForTtl(dic, 'odds', 'xsd:decimal')
        odds_rank = castDataForTtl(dic, 'odds_rank', 'xsd:decimal')
        sex = castDataForTtl(dic, 'sex')
        age = castDataForTtl(dic, 'age', 'xsd:unsignedByte')
        weight = castDataForTtl(dic, 'weight', 'xsd:decimal')
        gain = castDataForTtl(dic, 'gain', 'xsd:decimal')
        impost = castDataForTtl(dic, 'impost', 'xsd:decimal')
        racetime = castDataForTtl(dic, 'racetime', 'xsd:decimal')
        margin = castDataForTtl(dic, 'margin')
        passing_order = castDataForTtl(dic, 'passing_order')
        spurt = castDataForTtl(dic, 'spurt', 'xsd:decimal')
        jockey = '\"Unknown\"' if dic['jockey'] is NaN or not pattern_id.match(dic['jockey']) \
            else f'jockey:{dic["jockey"].zfill(6)}'
        trainer = '\"Unknown\"' if dic['trainer'] is NaN or not pattern_id.match(dic['trainer']) \
            else f'trainer:{dic["trainer"].zfill(5)}'
        owner = '\"Unknown\"' if dic['owner'] is NaN or not pattern_id.match(dic['owner']) \
            else f'owner:{dic["owner"].zfill(6)}'
        prize_money = castDataForTtl(dic, 'prize_money', 'xsd:decimal')

        horseInfo = ' ;\n\t'.join([
            f'\thorse:profile horse:{horse_id}',  # 馬情報
            f'\thorse:finishing_order {finishing_order}',  # 着順
            f'\thorse:post_position {post_position}',  # 枠番
            f'\thorse:horse_number {horse_number}',  # 馬番
            f'\thorse:odds {odds}',  # 単勝
            f'\thorse:odds_rank {odds_rank}',  # 人気
            f'\thorse:sex {sex}',  # 性別
            f'\thorse:age {age}',  # 馬齢
            f'\thorse:weight {weight}',  # 体重
            f'\thorse:gain {gain}',  # 前走比体重増減
            f'\thorse:impost {impost}',  # 斤量；負担重量
            f'\thorse:racetime {racetime}',  # タイム
            f'\thorse:margin {margin}',  # 着差
            f'\thorse:passing_order {passing_order}',  # 通過順
            f'\thorse:spurt {spurt}',  # 上がり（スパートタイム）
            f'\thorse:jockey {jockey}',  # 騎手
            f'\thorse:trainer {trainer}',  # 調教師
            f'\thorse:owner {owner}',  # 馬主
            f'\thorse:prize_money {prize_money}',  # 賞金(万円)
        ])

        runners += f'\t[ {horseInfo} ]\n '

    return f'\n{runners}\t'


def raceTemplate(race_id, row, cols_dividend, df) -> str:

    title = Unknown if row["title"] is NaN else row["title"].strip()
    date = Unknown if row["date"] is NaN else reformatDate(row["date"])
    start_at = Unknown if row["start_at"] is NaN else row["start_at"]
    track = Unknown if row["track"] is NaN else 'ダート' if row["track"] == 'ダ' else row["track"]
    direction = Unknown if row["direction"] is NaN else row["direction"]
    distance = Unknown if row["distance"] is NaN else row["distance"]
    weather = Unknown if row["weather"] is NaN else row["weather"]
    going = Unknown if row["going"] is NaN else row["going"]
    round = Unknown if row["round"] is NaN else row["round"]
    place = Unknown if row["place"] is NaN else row["place"]
    days = Unknown if row["days"] is NaN else row["days"]
    grade = Unknown if row["grade"] is NaN else row["grade"]
    requirement = Unknown if row["requirement"] is NaN else row["requirement"]
    rule = Unknown if row["rule"] is NaN else row["rule"]

    spacing_on_corner = cornerRank([
        row[col] for col in (f'spacing_on_corner:{i+1}' for i in range(4)) if row[col] is not NaN
    ])
    laptime = Unknown if row["laptime"] is NaN else row["laptime"]
    pacemaker = Unknown if row["pacemaker"] is NaN else row["pacemaker"]

    runners = getRunners(race_id, df)

    # 配当，人気，的中が含まれるカラムを抜き出す
    dividends = getDividends(row, cols_dividend)

    return '\n'.join([
        f'race:{race_id} race:title \"{title}\" ;',
        f'\trace:date \"{date}\" ;',
        f'\trace:start_at \"{start_at}\" ;',
        f'\trace:track \"{track}\" ;',
        f'\trace:direction \"{direction}\" ;',
        f'\trace:distance \"{distance}\" ;',
        f'\trace:weather \"{weather}\" ;',
        f'\trace:going \"{going}\" ;',
        f'\trace:round \"{round}\" ;',
        f'\trace:place \"{place}\" ;',
        f'\trace:days \"{days}\" ;',
        f'\trace:grade \"{grade}\" ;',
        f'\trace:requirement \"{requirement}\" ;',
        f'\trace:rule \"{rule}\" ;',
        f'\trace:spacing_on_corner {spacing_on_corner} ;',
        f'\trace:laptime \"{laptime}\" ;',
        f'\trace:pacemaker \"{pacemaker}\" ;',
        f'\trace:runners ({runners}) ;',
        f'\trace:dividends ({dividends}) .'
    ])


def col2dict(row, columns):
    return {name: row[name] for name in columns}


def processRace(filepath: Path):

    # まずはともあれDFを得る
    # 全体を文字列（str 型）として読み込む；ただし欠損値は float 型として扱われる
    df = pd.read_csv(filepath, sep='\t', header=0, index_col=0, dtype=str)

    # 一行ごとに処理する：ついでに残った「通算成績」もパースしておく
    columns = df.columns

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_dict = {
            executor.submit(col2dict, row, columns): str(race_id) for race_id, row in df.iterrows()
        }
        raceDict = {
            future_to_dict[future]: future.result() for future in concurrent.futures.as_completed(future_to_dict)
        }

    # original
    # raceDict = {
    #     str(race_id): {name: row[name] for name in columns} for race_id, row in df.iterrows()
    # }

    filepath_res = filepath.parent.with_name('result') / filepath.name
    df_result = pd.read_csv(filepath_res, sep='\t', header=0,  dtype=str)
    df_result.rename(columns={
        "着順": "finishing_order",
        "枠番": "post_position",
        "馬番": "horse_number",
        "単勝": "odds",
        "人気": "odds_rank",
        "馬名": "horse_id",
        "斤量": "impost",
        "タイム": "racetime",
        "着差": "margin",
        "通過": "passing_order",
        "上り": "spurt",
        "騎手": "jockey",
        "調教師": "trainer",
        "馬主": "owner",
        "賞金(万円)": "prize_money"
    }, inplace=True)

    columns_dividend = [
        col for col in columns if pattern_dividend.match(col[::-1])
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_list = [
            executor.submit(raceTemplate, race_id, row, columns_dividend, df_result) for race_id, row in raceDict.items()
        ]
        # raceDict を ttl 文字列に加工する
        ttl = '\n'.join([
            future.result() for future in concurrent.futures.as_completed(future_to_list)
        ])

    # # raceDict を ttl 文字列に加工する
    # ttl = '\n'.join([raceTemplate(race_id, row, columns_dividend, df_result)
    #                 for race_id, row in raceDict.items()])

    # 拡張子を ttl に変える＆＆ディレクトリを `turtle` 以下に変更してからファイルに書き出す
    outputPath = Path(
        # csv と一致したら turtle に変える
        *[path if path != 'csv' else 'turtle' for path in filepath.with_suffix('.ttl').parts]
    )
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    outputPath.unlink(missing_ok=True)
    outputPath.write_text(f'{PREFIX}\n\n{ttl}', encoding='utf-8')
