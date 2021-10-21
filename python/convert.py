
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


# and create `initialLoader.sql` ----------------------------------------------
TTL_LOADER = TTL_DIR / 'initialLoader.sql'
TTL_HORSE_DIR = TTL_DIR / 'horse'
TTL_RACE_DIR = TTL_DIR / 'race'

# 行末のセミコロンを忘れずに！
pre = """
log_enable(2,1);
"""

MOUNT_FOLDER = '/mount/data'


def compositeSQL(dir) -> str:
    res = ''
    for filepath in dir.glob('**/*.ttl'):
        filename = filepath.name
        parts = list(filepath.parts)
        idx = parts.index('turtle')
        relativeParent = '/'.join(parts[idx:-1])
        sql = "ld_dir(" \
            + f"'{MOUNT_FOLDER}/{relativeParent}/', " \
            + f"'{filename}', " \
            + f"'http://opendata.netkeiba.com/{relativeParent}/{filename}#');"
        res += f'{sql}\nrdf_loader_run();\ncheckpoint;\n\n'
    return res


# 'initialLoader.sql' にファイルごとに必要なSQL文を書き込む
with TTL_LOADER.open(encoding='utf-8', mode='w') as f:
    f.write(pre + '\n')
    f.write(compositeSQL(TTL_HORSE_DIR))
    f.write(compositeSQL(TTL_RACE_DIR))
