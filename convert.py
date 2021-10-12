
"""
data/csv/horse を走査（bms,sire は別）
ファイルごとに処理する

df として読み込む
prefix なしで ttl に変換
出力用ファイルにPREFIXESを書き出し
出力用ファイルにttl を一つづつ追記
完成
"""

from pathlib import Path
from tqdm import tqdm

from horseTsv2Ttl import processHorse


PREFIX = """
@prefix netkeiba: <https://db.netkeiba.com/> .
@prefix horse: <https://db.netkeiba.com/horse/> .

@prefix relation: <https://db.netkeiba.com/horse/ped#> .
@prefix race: <https://db.netkeiba.com/race/> .
"""

BASE_DIR = Path.cwd()
DUMP_TTL = BASE_DIR / 'dump.ttl'
HORSE_DIR = BASE_DIR / 'data' / 'csv' / 'horse'
HORSE_FILES = sorted(list(HORSE_DIR.glob('*.tsv')))

# ファイルごとにさせたい処理を挿入
for filepath in tqdm(HORSE_FILES):
    # prefix なしで ttl に変換
    processHorse(filepath)

# dumpTtl にPrefixを書き込む
DUMP_TTL.unlink()
DUMP_TTL.write_text(f'{PREFIX}\n', encoding='utf-8')

for filepath in tqdm(HORSE_DIR.glob('*.ttl'), total=len(HORSE_FILES)):
    # dumpTtl に追記していく
    with DUMP_TTL.open(mode='a', encoding='utf-8') as f:
        f.write(filepath.read_text(encoding='utf-8') + '\n')

# TODO: 最後にValidatorを噛ませたい


# -----------------------------------------------------------------------------

# RACE_DIR = BASE_DIR / 'data' / 'csv' / 'race'
# RACE_DIR = set(HORSE_DIR.glob('*.tsv'))
# TOTAL_HORSE_FILES = len(HORSE_FILES)
