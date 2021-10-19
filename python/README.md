# python scripts

#### `convert.py`

1. scrap してきた `*.tsv` ファイルを `*.ttl` 形式に変換する
2. ttl を bulk load するための Virtuoso 専用 SQL を準備する

- `horseTsv2Ttl.py` : `/data/csv/horse` 直下にある競走馬情報を変換する（`sire`, `bms` は別）
- `raceTsv2Ttl.py`: `/data/csv/race` 以下にあるすべてのレース情報を変換する
- `/data/turtle/initialLoader.sql`: ttl を Virtuoso に読み込むためのスクリプト
