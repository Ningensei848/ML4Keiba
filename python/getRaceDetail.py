import asyncio
import csv
import os
import re
import sys
import time
from pathlib import Path
from random import uniform

import aiohttp
import async_timeout
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
ENTRYPOINT = generateEntrypoints()

TRANSLATE_RESULT_COLS = {
    "着順": "rank",
    "枠番": "waku",
    "馬番": "umaban",
    "馬名": "horse",
    "性齢": "barei",
    "斤量": "impost",
    "騎手": "jockey",
    "タイム": "time",
    "着差": "diff",
    "通過": "rank_at_corner",
    "上り": "max_speed",
    "単勝": "odds",
    "人気": "ninki",
    "馬体重": "weight, gain",
    "調教師": "trainer",
    "馬主": "owner",
    "賞金(万円)": "bounty",
}


pattern_waku = re.compile(r"Waku")
pattern_umaban = re.compile(r"Umaban")


def main(race_list, target="shutuba", limit=3):
    os.environ["TARGET_TABLE"] = target
    # coroutine の返り値は 出走馬の一覧 (List[horse_id])
    shutuba_list = execAsync(races=race_list, coro=coroutine, limit=limit)
    shutuba_list = [race for race in shutuba_list if race is not None]
    horse_id_list = [row["horse_id"] for race in shutuba_list for row in race if row is not None and "horse_id" in row]
    return horse_id_list


async def coroutine(race_id, response):
    # coroutine の返り値は 出走馬の一覧 (List[horse_id])
    if response is None:
        return

    content = await response.text(encoding=ENCODING)
    time.sleep(2 + uniform(1, 10) / 10)
    soup = BeautifulSoup(content, "lxml")
    shutuba_list = [flattenShutubaList(row) for row in getShutubaList(soup)]
    outputShutubaList(race_id, shutuba_list)
    return shutuba_list


async def _fetch(session, race_id, coro):
    """HTTPリソースからデータを取得しコルーチンを呼び出す
    :param session: aiohttp.ClientSessionインスタンス
    :param url: アクセス先のURL
    :param coro: urlとaiohttp.ClientResponseを引数に取るコルーチン
    :return: coroの戻り値
    """
    url = (
        f"https://db.netkeiba.com/race/{race_id}"
        if os.environ.get("TARGET_TABLE") == "result"
        else f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
    )
    params = {"key": API_KEY, "url": url, "encoding": ENCODING}
    entrypoint = next(ENTRYPOINT)

    async with async_timeout.timeout(45):
        try:
            response = await session.get(f"{ENDPOINT}/{entrypoint}", params=params)
        except ClientError as e:
            print(e)
            response = None
    return await coro(race_id, response)


async def _bound_fetch(semaphore, race_id, session, coro):
    """並列処理数を制限しながらHTTPリソースを取得するコルーチン
    :param semaphore: 並列数を制御するためのSemaphore
    :param session: aiohttp.ClientSessionインスタンス
    :param url: アクセス先のURL
    :param coro: urlとaiohttp.ClientResponseを引数に取るコルーチン
    :return: coroの戻り値
    """
    async with semaphore:
        try:
            return await _fetch(session, race_id, coro)
        except asyncio.exceptions.TimeoutError as e:
            print(e, file=sys.stderr)
            return


async def _run(races, coro, limit=1):
    """並列処理数を制限しながらHTTPリソースを取得するコルーチン
    :param urls: URLの一覧
    :param coro: urlとaiohttp.ClientResponseを引数に取るコルーチン
    :param limit: 並列実行の最大数
    :return: coroの戻り値のリスト。urlsと同順で返す
    """
    semaphore = asyncio.Semaphore(limit)
    # [SSL: CERTIFICATE_VERIFY_FAILED]エラーを回避する
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        tasks = [asyncio.ensure_future(_bound_fetch(semaphore, race_id, session, coro)) for race_id in races]
        responses = await tqdm.gather(*tasks)  # wrapper for asyncio.gather
        return responses


def execAsync(races, coro, limit=3):
    """並列処理数を制限しながらHTTPリソースを取得し、任意の処理を行う
    :param urls: URLの一覧
    :param coro: urlとaiohttp.ClientResponseを引数に取る任意のコルーチン
    :param limit: 並列実行の最大数
    :return: coroの戻り値のリスト。urlsと同順。
    """
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(_run(races, coro, limit))
    return results


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


def processShutubaTag(row):

    if row is None:
        return

    tag = {
        "waku": row.find("td", class_=pattern_waku),
        "umaban": row.find("td", class_=pattern_umaban),
        "horse": row.find("span", class_="HorseName"),
        "barei": row.find("td", class_="Barei"),
        "impost": row.find("td", class_="Barei").next_sibling if row.find("td", class_="Barei") else None,  # 負担重量
        "jockey": row.find("td", class_="Jockey"),
        "trainer": row.find("td", class_="Trainer"),
        "weight": row.find("td", class_="Weight"),
        "odds": row.find("td", class_="Popular"),
        "ninki": row.find("td", class_="Popular_Ninki"),
    }

    if tag["impost"] == "\n":
        tag["impost"] = tag["impost"].next_sibling

    weight, gain = (
        getWeight(tag["weight"].get_text().strip())
        if tag["weight"] is not None and len(tag["weight"].get_text())
        else (None, None)
    )

    res = {
        "waku": tag["waku"].get_text() if tag["waku"] is not None else None,
        "umaban": tag["umaban"].get_text() if tag["umaban"] is not None else None,
        "horse": {"id": getId(tag["horse"].a["href"]), "name": tag["horse"].a["title"]},
        "barei": tag["barei"].get_text() if tag["barei"] is not None else None,
        "impost": tag["impost"].get_text() if tag["impost"] is not None else None,
        "jockey": {"id": getId(tag["jockey"].a["href"]), "name": tag["jockey"].a["title"]},
        "trainer": {"id": getId(tag["trainer"].a["href"]), "name": tag["trainer"].a["title"]},
        "weight": weight,  # tag["weight"].get_text().strip()
        "gain": gain
        # odds, ninki はJS側で処理しているらしく，単純なリクエストでは取得できない
        # "odds": tag["odds"].string,
        # "ninki": tag["ninki"].string
    }
    # 数値の型変換
    res["impost"] = float(res["impost"]) if is_num(res["impost"]) else res["impost"]
    res["weight"] = int(float(res["weight"])) if is_num(res["weight"]) else res["weight"]
    res["gain"] = int(float(res["gain"])) if is_num(res["gain"]) else res["gain"]

    return res


def processResultTag(row, headers):
    if row is None:
        return

    temp = {}
    for th, td in zip(headers, row.find_all("td")):
        if td.find("a"):
            temp[th] = {"id": getId(td.a["href"]), "name": td.a["title"]}
        else:
            temp[th] = td.get_text().strip()

    # pprint(res)
    weight, gain = getWeight(temp["馬体重"]) if temp["馬体重"] is not None and len(temp["馬体重"]) else (None, None)
    res = {}
    for k, v in TRANSLATE_RESULT_COLS.items():
        if k == "馬体重":
            res["weight"] = int(float(weight)) if is_num(weight) else weight
            res["gain"] = int(float(gain)) if is_num(gain) else gain
        else:
            res[v] = temp[k]

    # 数値の型変換
    res["rank"] = int(float(res["rank"])) if is_num(res["rank"]) else res["rank"]
    res["impost"] = float(res["impost"]) if is_num(res["impost"]) else res["impost"]
    res["diff"] = float(res["diff"]) if is_num(res["diff"]) else res["diff"]
    res["max_speed"] = float(res["max_speed"]) if is_num(res["max_speed"]) else res["max_speed"]
    res["odds"] = float(res["odds"]) if is_num(res["odds"]) else res["odds"]
    res["ninki"] = int(float(res["ninki"])) if is_num(res["ninki"]) else res["ninki"]
    res["weight"] = int(float(res["weight"])) if is_num(res["weight"]) else res["weight"]
    res["gain"] = int(float(res["gain"])) if is_num(res["gain"]) else res["gain"]
    if len(res["bounty"]):
        res["bounty"] = float(res["bounty"]) if is_num(res["bounty"]) else res["bounty"]
    else:
        res["bounty"] = None

    return res


def getShutubaList(soup):

    # `/race/shutuba.html?race_id=YYYYPPNNDDRR`
    # table.Shutuba_Table を取得する
    if os.environ.get("TARGET_TABLE") == "result":
        table = soup.find("table")
        if table is None:
            return []

        rows = [row for row in table.find_all("tr")]
        headers = [th.get_text() for th in rows[0].find_all("th")]

        return [processResultTag(row, headers) for row in rows[1:] if row is not None]
    else:
        table = soup.find("table", class_="Shutuba_Table")

        if table is None:
            return []

        return [processShutubaTag(row) for row in table.find_all("tr", class_="HorseList") if row is not None]


def flattenShutubaList(row):
    temp = {}
    for key, value in row.items():
        if type(value) is dict:
            for k, v in value.items():
                temp[f"{key}_{k}"] = v
        else:
            temp[key] = value
    return temp


def outputShutubaList(race_id, shutuba_list):
    if len(race_id) != 12:
        print(f"race_id is {race_id}", file=sys.stderr)
        raise ValueError("race_id is must be 12 digits!")

    if len(shutuba_list) < 1:
        return

    cwd = Path.cwd()
    race_id = str(race_id)
    yyyy, pp, nn, dd, rr = race_id[:4], race_id[4:6], race_id[6:8], race_id[8:10], race_id[10:]
    filepath = cwd / "data" / "race" / "csv" / yyyy / pp / nn / dd / f"{rr}.tsv"
    filepath.parent.mkdir(parents=True, exist_ok=True)  # 遡って親ディレクトリを作成

    headers = list(shutuba_list[0].keys())

    # 書き込み
    with filepath.open(mode="w", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        writer.writerows([list(row.values()) for row in shutuba_list])

    return


if __name__ == "__main__":

    args = sys.argv

    race_list = args[1:]

    if len(race_list) == 0:
        print("Please specify ID(s) as argument")
        sys.exit(1)

    # coroutine の返り値は 出走馬の一覧 (List[horse_id])
    shutuba_list = execAsync(races=race_list, coro=coroutine)

    shutuba_list = [race for race in shutuba_list if race is not None]

    horse_id_list = [row["horse_id"] for race in shutuba_list for row in race if row is not None and "horse_id" in row]
    print(horse_id_list)
    print("total:", len(horse_id_list))
