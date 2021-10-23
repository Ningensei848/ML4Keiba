import sys
import traceback
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

from tqdm import tqdm


# main ----------------------------------------------------------------------------------------
# year = 2018
# targetFile = DIR_LIST_HORSE / f'{year}.txt'
# id_list = [x for x in targetFile.read_text().split('\n') if x != '']

from myScrapLib import isProcessed, trackAncestor, prettifyDataset, makeCommands, Notify2LINE

BASE_DIR = Path.cwd().parent  # ML4Keiba


def now():
    return datetime.now(timezone(timedelta(hours=9)))


def main():

    DATA_ROOT = BASE_DIR / 'data'
    DIR_LIST = DATA_ROOT / 'list'
    DIR_LIST_HORSE = DIR_LIST / 'horse'

    loop_num = 0
    total = len(list(DIR_LIST_HORSE.glob('**/*.txt')))

    fileList = [x for x in DIR_LIST_HORSE.glob(
        '**/*.txt') if x.stem.isdecimal()]
    # fileList.sort(reverse=True)
    fileList.sort(reverse=False)
    fileList.extend([x for x in DIR_LIST_HORSE.glob(
        '**/*.txt') if not x.stem.isdecimal()])

    timing = datetime.now(timezone(timedelta(hours=9)))

    for targetFile in fileList:

        loop_num += 1

        id_list = [x for x in targetFile.read_text().split('\n') if x != '']

        count = 0

        for horse_id in tqdm(id_list):

            count += 1

            if isProcessed(horse_id):
                continue

            # horse_id から祖先をたどって行き着くまですべて処理
            trackAncestor(horse_id, 0)

            if now() > timing:
                timing = now() + timedelta(hours=8)  # timing を 8時間後に設定

                prettifyDataset()

                if len(sys.argv) > 1 and sys.argv[1] == '--production':
                    for proc in makeCommands():
                        subprocess.run(proc, encoding='utf-8',
                                       stdout=subprocess.PIPE)

                percentage = 100 * count / len(id_list)
                Notify2LINE(
                    f'【Git process】{targetFile.name} ({loop_num}/{total}) is {int(percentage)}% completed.')
            # --------------------------------------------------------------------
        # ----------------------------------------------------------------------
        # file 一つ終わったら報告 -------------------------------------------
        Notify2LINE(
            f'【Git process】{targetFile.name} ({loop_num}/{total}) is completed!')
    # end main for-loop ----------------------------------------------------
    # ----------------------------------------------------------------------
    # 全部終わったら報告 --------------------------------------------------------------------------------------
    Notify2LINE(
        f'【Git process】Fully Complete task ! Please stop the server!! => https://manage.conoha.jp/')
    # -------------------------------------------------------------------------------------------------------


for _ in range(3):
    try:
        main()
    except Exception as e:
        Notify2LINE(f'【ALERT】Process Down: \n => {traceback.format_exc()}')
