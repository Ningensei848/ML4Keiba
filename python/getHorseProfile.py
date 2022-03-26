# asyncio, aiohttpを利用した並列処理のサンプルコード | GitHub Gist
# cf. https://gist.github.com/rhoboro/86629f831934827d832841709abfe715

import asyncio
import csv
import datetime
import itertools
import json
import os
import re
import sys
import time

# import urllib.parse
from pathlib import Path
from random import uniform

import aiohttp
import async_timeout
import pandas as pd
from aiohttp import ClientError
from bs4 import BeautifulSoup

# .env ファイルをロードして環境変数へ反映
# cf. https://github.com/theskumar/python-dotenv#getting-started
from dotenv import load_dotenv
from libs.entrypoint import generateEntrypoints
from libs.validate import is_num
from tqdm.asyncio import tqdm

# from typing import Dict, List, Set, Tuple


load_dotenv()  # take environment variables from .env.

ENDPOINT = os.environ.get("ENDPOINT")
API_KEY = os.environ.get("API_KEY")
ENCODING = os.environ.get("ENCODING")

CONTEXT_JSONLD = (
    "https://raw.githubusercontent.com/Ningensei848/ML4Keiba/main/context.jsonld"  # @param {type:"string"}
)


ENTRYPOINT = generateEntrypoints()


DELETE_COLUMNS = ["開催", "レース名", "映像", "騎手", "距離", "馬場指数", "ﾀｲﾑ指数", "馬体重", "厩舎ｺﾒﾝﾄ", "備考", "勝ち馬(2着馬)", "賞金"]

# 祖先の relationships を生成
# parent = ['父', '母']
parent = ["F", "M"]
grandParent = ["".join(x) for x in itertools.product(parent, repeat=2)]
g1_grandParent = ["".join(x) for x in itertools.product(grandParent, parent)]
g2_grandParent = ["".join(x) for x in itertools.product(g1_grandParent, parent)]
g3_grandParent = ["".join(x) for x in itertools.product(g2_grandParent, parent)]
RELATIONSHIPS = [parent, grandParent, g1_grandParent, g2_grandParent, g3_grandParent]

SEP = "@@@@@"

TRANSLATE_DICT = {
    "生年月日": "birthday",
    "調教師": "trainer",
    "馬主": "owner",
    "生産者": "breeder",
    "産地": "birthplace",
    "セリ取引価格": "price",
    "獲得賞金": "bounty",
}

RESULT_HEADER = [
    # result = getHorseResult(soup)
    # for res in result:
    #     for key in res.keys():
    #         print(f'"{key}",')
    "日付",
    "天気",
    "R",
    "頭数",
    "枠番",
    "馬番",
    "オッズ",
    "人気",
    "着順",
    "斤量",
    "馬場",
    "タイム",
    "着差",
    "通過",
    "ペース",
    "上り",
    "place",
    "race_id",
    "race_name",
    "movie",
    "jockey",
    "field",
    "distance",
    "weight",
    "gain",
    "bounty",
]

# regexp

pattern_waku = re.compile(r"Waku")
pattern_umaban = re.compile(r"Umaban")

pattern_katakana = re.compile("[\u30A1-\u30FF]+")
pattern_english_name = re.compile(r"\(.+\)")


def getId(url: str) -> str:
    return url.strip("/").split("/")[-1]


def getWeight(text):

    text = text.strip("）").strip(")")

    if "(" in text:
        return text.split("(")  # 半角
    elif "（" in text:
        return text.split(r"（")  # 全角
    else:
        return text, None


def getBirthday(birth: str):
    try:
        ymd = datetime.datetime.strptime(birth, "%Y年%m月%d日")
        return ymd.strftime("%Y/%m/%d")
    except ValueError:
        # 生年しかわからない場合
        m = re.match(r"[0-9]+", birth)
        if not m:
            return None
        else:
            return m.group()


def getTotalResult(text):
    first, second, third, others = re.split(r"\D", text)
    return {"first": first, "second": second, "third": third, "others": others}


def getHorseResult(soup):
    # `/horse/YYYYXXXXXX`
    db_h_race_results = soup.find("table", class_="db_h_race_results")

    if db_h_race_results is None:
        return

    thead = [th.get_text().strip() for th in db_h_race_results.thead.find_all("th")]
    return [processHorseResult(row, thead) for row in db_h_race_results.tbody.find_all("tr")]


def processHorseResult(row, thead):
    temp = {key: col for key, col in zip(thead, row.find_all("td"))}
    # 開催，レース名，映像，騎手，勝ち馬については，別途処理
    weight, gain = getWeight(temp["馬体重"].get_text()) if len(temp["馬体重"].get_text()) else (None, None)

    res = {
        "place": re.sub(r"\d", "", temp["開催"].get_text()) if temp["開催"].find("a") else None,
        "race_id": getId(temp["レース名"].a["href"]) if temp["レース名"].find("a") else None,
        "race_name": temp["レース名"].get_text() if temp["レース名"].find("a") else None,
        "movie": getId(temp["映像"].a["href"]) if temp["映像"].find("a") else None,
        "jockey": getId(temp["騎手"].a["href"]) if temp["騎手"].find("a") else None,
        "field": re.sub(r"\d", "", temp["距離"].get_text()) if len(temp["距離"].get_text()) else None,
        "distance": re.sub(r"[^\d]", "", temp["距離"].get_text()) if len(temp["距離"].get_text()) else None,
        "weight": weight,
        "gain": gain,
        "bounty": temp["賞金"].get_text().strip().replace(",", "") if len(temp["賞金"].get_text().strip()) else str(0),
    }
    # 数値の型変換
    res["distance"] = int(float(res["distance"])) if is_num(res["distance"]) else res["distance"]
    res["weight"] = int(float(res["weight"])) if is_num(res["weight"]) else res["weight"]
    res["gain"] = int(float(res["gain"])) if is_num(res["gain"]) else res["gain"]
    res["bounty"] = float(res["bounty"]) if is_num(res["bounty"]) else res["bounty"]

    # 不要なカラムを削除
    for col in DELETE_COLUMNS:
        del temp[col]

    temp = {key: value.get_text().strip() for key, value in temp.items()}

    # 数値の型変換
    temp["オッズ"] = float(temp["オッズ"]) if is_num(temp["オッズ"]) else temp["オッズ"]
    temp["斤量"] = float(temp["斤量"]) if is_num(temp["斤量"]) else temp["斤量"]
    temp["着差"] = float(temp["着差"]) if is_num(temp["着差"]) else temp["着差"]
    temp["上り"] = float(temp["上り"]) if is_num(temp["上り"]) else temp["上り"]

    temp.update(res)

    for k, v in temp.items():
        if v == "":
            temp[k] = None
        else:
            continue

    return temp


def getHorseMeta(soup):
    # `/horse/YYYYXXXXXX`
    db_main_box = soup.find(id="db_main_box")

    if db_main_box is None:
        return

    horse_title = db_main_box.find("div", class_="horse_title")
    db_prof_table = db_main_box.find("table", class_="db_prof_table")

    # horse_title が None なら，そのページは存在しない（はず）
    if horse_title is None:
        return

    # rate が存在する場合，邪魔なので削除
    if horse_title.find("p", class_="rate"):
        horse_title.find("p", class_="rate").extract()

    temp = horse_title.p.get_text().split()

    if len(temp) == 3:
        status, sei, color = temp
        sei = re.sub(r"\d+歳", "", sei)
        # TODO: sei のうち，X歳を削除（re.sub）
    elif len(temp) == 2:
        status = None
        sei, color = temp
    elif len(temp) == 1:
        status, color = None, None
        sei = temp[0]
    else:
        status, sei, color = None, None, None

    prof_table = {"name": horse_title.h1.get_text().strip(), "status": status, "sex": sei, "color": color}

    prof_table.update({row.th.get_text(): row.td for row in db_prof_table.find_all("tr")})

    prof_table["生年月日"] = getBirthday(prof_table["生年月日"].get_text())
    prof_table["調教師"] = (
        {
            "@id": "trainer:" + getId(prof_table["調教師"].a["href"]),
            "@type": "ml4keiba:Trainer",
            "name": prof_table["調教師"].a.get_text(),
        }
        if prof_table["調教師"].find("a")
        else None
    )

    prof_table["馬主"] = (
        {
            "@id": "owner:" + getId(prof_table["馬主"].a["href"]),
            "@type": "ml4keiba:Owner",
            "name": prof_table["馬主"].a.get_text(),
            "silks": prof_table["馬主"].img["src"] if prof_table["馬主"].find("img") else None,
        }
        if prof_table["馬主"].find("a")
        else None
    )

    prof_table["生産者"] = (
        {
            "@id": "breeder:" + getId(prof_table["生産者"].a["href"]),
            "@type": "ml4keiba:Breeder",
            "name": prof_table["生産者"].a.get_text(),
        }
        if prof_table["生産者"].find("a")
        else None
    )

    sanchi = prof_table["産地"].get_text()
    prof_table["産地"] = sanchi if len(sanchi) else None

    price = prof_table["セリ取引価格"].get_text().strip()
    prof_table["セリ取引価格"] = price if price != "-" else None

    pattern_bounty = re.compile(r"[^0-9]+")
    bounty = prof_table["獲得賞金"].get_text().strip().replace(",", "")
    prof_table["獲得賞金"] = pattern_bounty.sub("", bounty) if len(bounty) else str(0)
    prof_table["獲得賞金"] = float(prof_table["獲得賞金"]) if prof_table["獲得賞金"].isdecimal() else prof_table["獲得賞金"]

    if prof_table["status"] != "現役":
        total_result = (
            getTotalResult(prof_table["通算成績"].a.get_text().strip()) if prof_table["通算成績"].find("a") else None
        )
        prof_table["result"] = total_result
    else:
        prof_table["result"] = None

    del prof_table["主な勝鞍"], prof_table["近親馬"], prof_table["通算成績"]

    return prof_table


def processHorseName(td):

    # return name_ja, name_en

    if len(td.a.get_text()) > 0 and td.a.string is None:
        temp = [x.get_text().strip() for x in td.a.children]
        m = pattern_katakana.match(temp[0])
        if not m:
            return None, temp[0]
        else:
            return temp[0], temp[-1]
    else:
        name = td.a.get_text().strip()
        m = pattern_katakana.match(name)
        if not m:
            return None, name
        else:
            return name, None


def getHorsePed(soup):
    # `/horse/ped/YYYYXXXXXX`

    blood_table = soup.find("table", class_="blood_table")

    # 前処理：余分な情報を消去して horse_id だけ残す
    for td in blood_table.find_all("td"):
        if td.a is None:
            td.string = "-" + SEP + "-"
            continue
        else:
            horse_id = td.a["href"].strip("/").split("/")[-1]
            name_ja, name_en = processHorseName(td)
            td.string = horse_id + SEP + f"{name_ja}/horse_name/{name_en}"

    dfs = pd.read_html(blood_table.prettify())
    df = dfs[0]

    ped = {}

    for gen in range(5):
        cells = df[gen].tolist()
        # range(start, stop, step)
        ancestors = [cells[i] for i in range(0, len(cells), 2 ** (4 - gen))]
        for r, ancestor in zip(RELATIONSHIPS[gen], ancestors):
            id, name = ancestor.split(SEP)
            name_ja, name_en = name.split("/horse_name/") if name != "-" else (None, None)
            if name_ja == "None":
                name_ja = None
            if name_en is not None:
                name_en = pattern_english_name.sub("", name_en) if name_en != "None" else None

            ped[r] = {
                "@id": f"horse:{id}",
                "@type": "ml4keiba:Horse",
                "name_ja": name_ja,
                "name_en": name_en,
            }

    return ped


def getHorseProfile(horse_id, meta, pedigree):

    horse_dict = {"@context": CONTEXT_JSONLD, "@id": f"horse:{horse_id}", "@type": "ml4keiba:Horse"}
    horse_dict.update({**meta, **{new_key: meta[key] for key, new_key in TRANSLATE_DICT.items()}, **pedigree})

    for key in TRANSLATE_DICT.keys():
        if key in horse_dict:
            del horse_dict[key]

    if "募集情報" in horse_dict:
        del horse_dict["募集情報"]

    return horse_dict


def outputHorseProfile(horse_id, profile):
    if len(horse_id) != 10:
        raise ValueError("horse_id is must be 10 digits!")

    cwd = Path.cwd()
    horse_id = str(horse_id)
    yyyy, xxxx, zz = horse_id[:4], horse_id[4:8], horse_id[8:]
    filepath = cwd / "data" / "horse" / "json" / "profile" / yyyy / xxxx / f"{zz}.json"
    filepath.parent.mkdir(parents=True, exist_ok=True)  # 遡って親ディレクトリを作成
    filepath.write_text(json.dumps(profile, indent=2, ensure_ascii=False))
    return


def outputHorseResult(horse_id, result):
    if len(horse_id) != 10:
        raise ValueError(f"horse_id is must be 10 digits! => {horse_id}")

    if result is None or len(result) < 1:
        return

    cwd = Path.cwd()
    horse_id = str(horse_id)
    yyyy, xxxx, zz = horse_id[:4], horse_id[4:8], horse_id[8:]
    filepath = cwd / "data" / "horse" / "csv" / "result" / yyyy / xxxx / f"{zz}.tsv"
    filepath.parent.mkdir(parents=True, exist_ok=True)  # 遡って親ディレクトリを作成
    # 書き込み
    with filepath.open(mode="w", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(RESULT_HEADER)
        writer.writerows([list(r.values()) for r in result])

    return


async def coroutine(horse_id, res_top, res_ped):

    if res_top is None or res_ped is None:
        return

    content_top = await res_top.text(encoding=ENCODING)
    content_ped = await res_ped.text(encoding=ENCODING)

    meta = getHorseMeta(BeautifulSoup(content_top, "lxml"))
    ped = getHorsePed(BeautifulSoup(content_ped, "lxml"))

    if meta is None or ped is None:
        return

    profile = getHorseProfile(horse_id, meta, ped)
    outputHorseProfile(horse_id, profile)

    result = getHorseResult(BeautifulSoup(content_top, "lxml"))

    try:
        outputHorseResult(horse_id, result)
    except ValueError as ve:
        print(ve, file=sys.stderr)

    return


async def requestAsync(session, url):
    params = {"key": API_KEY, "url": url, "encoding": ENCODING}
    entrypoint = next(ENTRYPOINT)
    url = f"{ENDPOINT}/{entrypoint}"

    async with async_timeout.timeout(45):
        try:
            response = await session.get(url, params=params)
        except ClientError as e:
            print(e)
            response = None
    return response


async def _fetch(session, horse_id, coro):
    """HTTPリソースからデータを取得しコルーチンを呼び出す
    :param session: aiohttp.ClientSessionインスタンス
    :param horse_id: アクセス先の horse_id
    :param coro: horse_id とaiohttp.ClientResponseを引数に取るコルーチン
    :return: coroの戻り値
    """
    horse_id = str(horse_id)
    res_top = await requestAsync(session, f"https://db.netkeiba.com/horse/{horse_id}")
    time.sleep(2 + uniform(1, 10) / 10)
    res_ped = await requestAsync(session, f"https://db.netkeiba.com/horse/ped/{horse_id}")

    return await coro(horse_id, res_top, res_ped)


async def _bound_fetch(semaphore, horse_id, session, coro):
    """並列処理数を制限しながらHTTPリソースを取得するコルーチン
    :param semaphore: 並列数を制御するためのSemaphore
    :param session: aiohttp.ClientSessionインスタンス
    :param horse_id: アクセス先の horse_id
    :param coro: horse_id とaiohttp.ClientResponseを引数に取るコルーチン
    :return: coroの戻り値
    """
    async with semaphore:
        try:
            return await _fetch(session, horse_id, coro)
        except asyncio.exceptions.TimeoutError as e:
            print(e, file=sys.stderr)
            return


async def _run(horse_list, coro, limit=1):
    """並列処理数を制限しながらHTTPリソースを取得するコルーチン
    :param horse_list: horse_id の一覧
    :param coro: horse_id　と aiohttp.ClientResponse を引数に取るコルーチン
    :param limit: 並列実行の最大数
    :return: coroの戻り値のリスト。urlsと同順で返す
    """
    tasks = []
    semaphore = asyncio.Semaphore(limit)
    # [SSL: CERTIFICATE_VERIFY_FAILED]エラーを回避する
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        tasks = [asyncio.ensure_future(_bound_fetch(semaphore, horse_id, session, coro)) for horse_id in horse_list]
        responses = await tqdm.gather(*tasks)  # wrapper for asyncio.gather
        return responses


def main(horse_list, coro=coroutine, limit=12):
    """並列処理数を制限しながらHTTPリソースを取得し、任意の処理を行う
    :param urls: URLの一覧
    :param coro: urlとaiohttp.ClientResponseを引数に取る任意のコルーチン
    :param limit: 並列実行の最大数
    :return: coroの戻り値のリスト。urlsと同順。
    """
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_run(horse_list, coro, limit))
    return


if __name__ == "__main__":

    args = sys.argv

    horse_list = args[1:]

    if len(horse_list) == 0:
        print("Please specify ID(s) as argument")
        sys.exit(1)

    main(horse_list=horse_list, coro=coroutine, limit=12)
