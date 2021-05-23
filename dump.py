
import re
from pathlib import Path
from tqdm import tqdm

prefix = """
@prefix baken: <https://www.jra.go.jp/kouza/beginner/baken/#type_> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix horse_id: <https://db.netkeiba.com/horse/> .
@prefix jockey_id: <https://db.netkeiba.com/jockey/> .
@prefix owner_id: <https://db.netkeiba.com/owner/> .
@prefix race_id: <https://db.netkeiba.com/race/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <http://schema.org/> .
@prefix trainer_id: <https://db.netkeiba.com/trainer/> .
@prefix wd: <https://www.wikidata.org/entity/> .
@prefix wdt: <http://www.wikidata.org/prop/direct/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""

cwd = Path.cwd()

# @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
pattern_prefix = re.compile(r'@prefix\s+\w+:\s+<.*?>\s+\.')
dumpTtl = cwd / 'dump.ttl'
turtle = cwd / 'data' / 'turtle'


# dump.ttl が存在していれば削除する
if dumpTtl.exists():
    dumpTtl.unlink(missing_ok=True)


# ./data/turtle/ 以下の .ttl ファイルの一覧を探す
ttlPathList = list(turtle.glob('**/*.ttl'))

# 最初にPrefixだけ準備しておく
dumpTtl.write_text(prefix + '\n\n')


count = 0
data = prefix + '\n\n'

for fp in tqdm(ttlPathList):
    count += 1
    temp = fp.read_text(encoding='utf-8')
    text = pattern_prefix.sub('', temp)
    data += '\n\n' + text.strip()

    if count < 1024:
        continue
    else:
        with dumpTtl.open(encoding='utf-8', mode='a') as f:
            f.write(data)
            data = ''
            count = 0
        continue


with dumpTtl.open(encoding='utf-8', mode='a') as f:
    f.write(data)
