
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
from tqdm import tqdm



# main ----------------------------------------------------------------------------------------
# year = 2018
# targetFile = DIR_LIST_HORSE / f'{year}.txt'
# id_list = [x for x in targetFile.read_text().split('\n') if x != '']

from mylib import isProcessed, trackAncestor, prettifyDataset, makeCommands, Notify2LINE

cwd = Path.cwd()  # expected `/content/ML4Keiba`
DATA_ROOT = cwd / 'data'
DIR_LIST = DATA_ROOT / 'list'
DIR_LIST_HORSE = DIR_LIST / 'horse'

loop_num = 0
total = len(list(DIR_LIST_HORSE.glob('**/*.txt')))

for targetFile in DIR_LIST_HORSE.glob('**/*.txt'):

    loop_num += 1

    id_list = [x for x in targetFile.read_text().split('\n') if x != '']

    count = 0
    quarter = 0

    for horse_id in tqdm(id_list):

        if isProcessed(horse_id):
            continue

        # horse_id から祖先をたどって行き着くまですべて処理
        trackAncestor(horse_id, 0)

        # 一定数データが溜まったら整理 -----------------------------------------
        if count < (len(id_list) // 4):
            count += 1
        else:
            quarter += 1
            prettifyDataset()

            for proc in makeCommands():
                subprocess.run(proc, encoding='utf-8', stdout=subprocess.PIPE)

            percentage = 25 * quarter
            Notify2LINE(f'【Git process】{targetFile.name} ({loop_num}/{total}) is {percentage}% completed.')

            count = 0 # 初期化して再度ループ
        # --------------------------------------------------------------------
    # ----------------------------------------------------------------------
    # file 一つ終わったら報告 -------------------------------------------
    Notify2LINE(f'【Git process】{targetFile.name} ({loop_num}/{total}) is completed!')
# end main for-loop ----------------------------------------------------
# ----------------------------------------------------------------------
# 全部終わったら報告 --------------------------------------------------------------------------------------
Notify2LINE(f'【Git process】Fully Complete task ! Please stop the server!! => https://manage.conoha.jp/')
# -------------------------------------------------------------------------------------------------------


