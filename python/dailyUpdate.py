# https://{race|nar}.netkeiba.com/top/race_list_sub.html?kaisai_date={YYYYMMDD}' をシードとして，毎日のレース情報を収集する
# 各馬，騎手，調教師等の更新は一旦待機

import datetime
import os
import re
import subprocess

# from random import randint, uniform
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

# .env ファイルをロードして環境変数へ反映
# cf. https://github.com/theskumar/python-dotenv#getting-started
from dotenv import load_dotenv
from getHorseProfile import main as processHorseData
from getRaceDetail import main as updateRaceAndGetHorseList
from libs.entrypoint import generateEntrypoints
from libs.filter import filteringDuplicated
from libs.validate import is_num
from tqdm import tqdm

# import time


load_dotenv()  # take environment variables from .env.

ENDPOINT = os.environ.get("ENDPOINT")
API_KEY = os.environ.get("API_KEY")
PARALLEL_LIMIT = int(os.environ.get("PARALLEL_LIMIT", 12))
ENTRYPOINT = generateEntrypoints()
isBulk = os.environ.get("IS_BULK", False)
IS_BULK = bool(int(float(isBulk)) if is_num(isBulk) else isBulk)
print(f"Bulk execution: {str(IS_BULK)}")


pattern_race_id_in_list = re.compile(r".*race_id=(\w+)&?")


def main(date: int = None) -> List[str]:
    today = datetime.date.today()
    year, month, day = today.year * 10**4, today.month * 10**2, today.day

    target = year + month + day if date is None else date

    yyyy = None if date is None else datetime.datetime.strptime(str(date), "%Y%m%d").strftime("%Y")
    mm = None if date is None else datetime.datetime.strptime(str(date), "%Y%m%d").strftime("%B")

    race_today = getKaisaiList(target)

    # 当日に開催されるレースの一覧を取得してリストを更新
    updateRaceList(race_today["jra"], yyyy, mm)
    updateRaceList(race_today["nar"], yyyy, mm)

    # レースの情報を取得し保存，さらにレースに出走するすべての馬のID一覧を取得
    # horse_list = updateRaceAndGetHorseList(race_list=race_today, limit=PARALLEL_LIMIT)
    target = os.environ.get("RACE_TARGET_TABLE", "shutuba")
    horse_list_jra = updateRaceAndGetHorseList(
        race_list=race_today["jra"], race="jra", target=target, limit=PARALLEL_LIMIT
    )
    horse_list_nar = updateRaceAndGetHorseList(
        race_list=race_today["nar"], race="nar", target=target, limit=PARALLEL_LIMIT
    )

    # 大量に処理している場合，すでに処理してある horse_id を取り除く（重複処理をへらす）
    if IS_BULK:
        horse_list_jra = filteringDuplicated(horse_list_jra)
        horse_list_nar = filteringDuplicated(horse_list_nar)

    # 馬ごとのIDをもとに，その馬のプロファイルと戦績を取得
    horse_list = horse_list_jra + horse_list_nar
    processHorseData(horse_list=horse_list, limit=PARALLEL_LIMIT)

    # 昨日までに行われた結果の更新
    # 日付が指定されていれば，更新せず終了
    if date is not None:
        return  # 終了

    yester = today - datetime.timedelta(days=1)
    target = sum([yester.year * 10**4, yester.month * 10**2, yester.day])
    race_yesterday = getKaisaiList(target)

    # # レースの情報を取得し保存，さらにレースに出走するすべての馬のID一覧を取得
    updateRaceAndGetHorseList(race_list=race_yesterday["jra"], race="jra", target="result", limit=PARALLEL_LIMIT)
    updateRaceAndGetHorseList(race_list=race_yesterday["nar"], race="nar", target="result", limit=PARALLEL_LIMIT)

    return


def fetchDirectly(url: str) -> str:
    cmd = f"curl '{url}' | nkf -w --url-input"
    proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.stdout


def fetch(url, path=None):

    entrypoint = next(ENTRYPOINT)
    payload = {"key": API_KEY, "url": url}

    return requests.get(f"{ENDPOINT}/{entrypoint}", params=payload)


def getKaisaiRaceId(text: str) -> str:
    m = pattern_race_id_in_list.match(text)
    return m.group(1) if m else ""


def getKaisaiSource(kaisai_date: int) -> str:
    url = f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={kaisai_date}"
    return fetch(url).text


def getKaisaiSourceNAR(kaisai_date: int) -> str:
    url = f"https://nar.netkeiba.com/top/race_list_sub.html?kaisai_date={kaisai_date}"
    soup = BeautifulSoup(fetch(url).text, "lxml")
    # time.sleep(2 + uniform(1, 10) / 10)
    ul = soup.find("ul", class_="RaceList_ProvinceSelect")

    if ul is None:
        return ""

    params = [aTag["href"] for aTag in ul.find_all("a")]
    sources = []
    for param in tqdm(params, desc="NAR races ..."):
        sources.append(fetch(f"https://nar.netkeiba.com/top/race_list_sub.html{param}").text)
        # time.sleep(2 + uniform(1, 10) / 10)

    return "\n".join(sources)


def getKaisaiList(kaisai_date: int):

    jra = getKaisaiSource(kaisai_date)
    # time.sleep(2 + uniform(1, 10) / 10)
    nar = getKaisaiSourceNAR(kaisai_date)

    jraIds = filter(lambda a: len(a), [getKaisaiRaceId(line) for line in jra.split("\n")])
    narIds = filter(lambda a: len(a), [getKaisaiRaceId(line) for line in nar.split("\n")])

    return {
        "jra": sorted(list(set(jraIds))),
        "nar": sorted(list(set(narIds))),
    }


def updateRaceList(arr: List[str] = None, yyyy: str = None, mm: str = None) -> None:
    today = datetime.date.today()
    year = today.strftime("%Y") if yyyy is None else yyyy
    month = today.strftime("%B") if mm is None else mm

    filepath = Path.cwd() / "data" / "race" / "list" / str(year) / f"{month}.txt"
    # file が存在しなければ作る，存在していれば何もせずタイムスタンプだけ更新される
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.touch(exist_ok=True)

    text = filepath.read_text()
    ids = list(filter(lambda a: len(a), [line.strip() for line in text.split("\n")]))
    updatedList = sorted(list(set(ids + arr)))

    filepath.write_text("\n".join(updatedList) + "\n")

    return


if __name__ == "__main__":
    main()
