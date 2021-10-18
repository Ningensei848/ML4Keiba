
"""
data/csv/horse を走査（bms,sire は別）
ファイルごとに処理する

df として読み込む
prefix なしで ttl に変換
出力用ファイルにPREFIXESを書き出し
出力用ファイルにttl を一つづつ追記
完成
"""

import concurrent.futures
from pathlib import Path
from tqdm import tqdm
from horseTsv2Ttl import PREFIX, processHorse
from raceTsv2Ttl import processRace

PREFIX = """
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix horse: <https://db.netkeiba.com/horse/> .
@prefix trainer: <https://db.netkeiba.com/trainer/> .
@prefix owner: <https://db.netkeiba.com/owner/> .
@prefix jockey: <https://db.netkeiba.com/owner/> .
@prefix breeder: <https://db.netkeiba.com/breeder/> .

@prefix relation: <https://db.netkeiba.com/horse/ped#> .
@prefix race: <https://db.netkeiba.com/race/> .
@prefix baken: <https://db.netkeiba.com/race/baken/> .
"""
BASE_DIR = Path.cwd().parent  # /ML4Keiba

# DUMP_TTL = BASE_DIR / 'dump.ttl'
TTL_DIR = BASE_DIR / 'data' / 'turtle'


# horse -----------------------------------------------------------------------
HORSE_DIR = BASE_DIR / 'data' / 'csv' / 'horse'
# without sire/bms
HORSE_FILES = sorted(list(HORSE_DIR.glob('*.tsv')))
with concurrent.futures.ProcessPoolExecutor() as executor:
    list(tqdm(executor.map(processHorse, HORSE_FILES),
         total=len(HORSE_FILES), desc='multi processing @ process horse data'))

del HORSE_FILES  # for GC

# race ------------------------------------------------------------------------
RACE_DIR = BASE_DIR / 'data' / 'csv' / 'race'

# RACE_RESULT_FILES = sorted(list(RACE_DIR.glob('**/result/*.tsv')))
RACE_FILES = sorted(list(RACE_DIR.glob('**/stats/*.tsv')))
RACE_FILES_TOTAL = len(RACE_FILES)

with concurrent.futures.ProcessPoolExecutor() as executor:
    list(tqdm(executor.map(processRace, RACE_FILES),
         total=len(RACE_FILES), desc='multi processing @ process race data'))

del RACE_FILES  # for GC

# TODO: 最後にValidatorを噛ませたい

# output TTL ------------------------------------------------------------------

horse_dir, race_dir = (p for p in TTL_DIR.iterdir())

HORSE_TTL = BASE_DIR / 'virtuoso' / 'horse.ttl'
RACE_TTL = BASE_DIR / 'virtuoso' / 'race.ttl'

with HORSE_TTL.open(encoding='utf-8', mode='w') as f:
    f.write(PREFIX + '\n\n')
    for filepath in horse_dir.glob('**/*.ttl'):
        f.write(filepath.read_text())

with RACE_TTL.open(encoding='utf-8', mode='w') as f:
    f.write(PREFIX + '\n\n')
    for filepath in race_dir.glob('**/*.ttl'):
        f.write(filepath.read_text() + '\n')
