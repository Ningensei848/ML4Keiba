
"""
TSVファイルの filepath を受け取る
df として読み込む

<< prefix なしで ttl に変換 >>

ttl に書き出しまでやって終了
"""

from pathlib import Path
import pandas as pd
import itertools

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
        ' '.join([f'\trelation:{rel}', f'horse:{row[rel]}' if type(row[rel]) is not float else '\"unknown\"', ";"]) for rel in RELATIONSHIPS
    ]
    return '\n'.join(lines)


def getRaceHistory(row):
    if type(row['race_history']) is float:
        return '\thorse:race_history ()'

    races = [f'race:{race_id}' for race_id in row['race_history'].split('-->')]

    return f'\thorse:race_history ( {" ".join(races)} )'


def template(horse_id, row):
    return '\n'.join([
        f"horse:{horse_id} horse:stallion {row['stallion']} ;",
        f"\thorse:birthday \"{row['birthday']}\" ;",
        f"\thorse:trainer \"{row['trainer']}\" ;",
        f"\thorse:owner \"{row['owner']}\" ;",
        f"\thorse:breeder \"{row['breeder']}\" ;",
        f"\thorse:country \"{row['country']}\" ;",
        f"\thorse:sale_price \"{row['sale_price']}\" ;",
        f"\thorse:prize_total \"{row['prize_total']}\" ;",
        f"\thorse:win \"{row['win']}\" ;",
        f"\thorse:second \"{row['second']}\" ;",
        f" \thorse:third \"{row['third']}\" ;",
        f"\thorse:lose \"{row['lose']}\" ;",
        f"\thorse:race_total \"{row['race_total']}\" ;",
        getRelation(row),
        f"{getRaceHistory(row)} .\n"
    ])


def preprocessing(df):
    df.replace('True', 'true', inplace=True)
    df.replace('False', 'false', inplace=True)

    return df


def processHorse(filepath: Path):
    # csv の日本語を一部変換
    # 全体を文字列（str 型）として読み込む；ただし欠損値は float 型として扱われる
    df = renameColumns(pd.read_csv(
        filepath, sep='\t', header=0, index_col=0, dtype=str
    ))

    # df の前処理
    df = preprocessing(df)

    # 一行ごとに処理する：ついでに残った「通算成績」もパースしておく
    horseDict = processHorseDict({
        horse_id: {name: row[name] for name in df.columns} for horse_id, row in df.iterrows()
    })

    # horseDict を ttl 文字列に加工する
    ttl = '\n'.join([template(horse_id, row)
                     for horse_id, row in horseDict.items()])

    # 拡張子を ttl にしてファイルに書き出す
    outputPath = filepath.with_suffix('.ttl')
    outputPath.unlink()
    outputPath.write_text(ttl)
