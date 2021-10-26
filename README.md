# ML4Keiba: Machine Learning for `競馬` Dataset

## TL; DR

- 【 WIP 】Scraping from [netkeiba.com](https://www.netkeiba.com/)
- (TODO) Convert `RDF` data (for LOD)
- (TODO) Deploy to [triple server](https://en.wikipedia.org/wiki/Triplestore) (e.g. Amazon Neptune, Openlink Virtuoso, etc.)
- (Our target) Predict results of JRA horse racing

## memo

Virtuoso on docker による bulk_load cf. http://wiki.lifesciencedb.jp/mw/SPARQLthon75/virtuoso_docker

=> `ttl` フォルダを作ってマウントしてしまうのが良さそう

### ttl フォルダから bulk load する

```
nohup docker exec -i ml4keiba_virtuoso_1 isql 1111 -U dba -P password < ./data/turtle/initialLoader.sql &
```

[Example for Multiple RDF Source Files Upload](http://vos.openlinksw.com/owiki/wiki/VOS/VirtBulkRDFLoaderExampleMultiple)

[Bulk Loading RDF Source Files into one or more Graph IRIs](http://vos.openlinksw.com/owiki/wiki/VOS/VirtBulkRDFLoader)

caution: パフォーマンス・チューニングをしないと永劫に感じる時間がかかる場合がある

> 現状だと，30 分弱もかかっている！
> `Done. -- 1561629 msec.`

cf. http://vos.openlinksw.com/owiki/wiki/VOS/VirtRDFPerformanceTuning

### GCE 上で動かす？

- TTL は手元の PC で TSV から加工して，GCS(Google Cloud Storage) 上に移す

  - tsv => ttl 変換は計算リソースもストレージも食うので，ローカルでうまく加工しておきたい
  - GCE からバケツにアクセスするためには 1. `gcsfuse` でマウントする 2. `gsutil` が必要だが，_Container-Optimized OS_ にはいい感じのパッケージ管理ツールが搭載されていない

    - `google/cloud-sdk` っていうコンテナを関数として使いましょう（この中に `gsutil` があるので，いい感じにフォルダをマウントして扱う）
      - `mkdir data && gsutil -m cp -r gs://babieca/turtle data`

- ブートディスクは10だと足りないけど，20だと潤沢に余るようだった．折衷案は15くらいだろうか？
  - 一度増やすと減らせないので注意（インスタンス作り直しになる）
- cloud-init の話：https://cloud.google.com/container-optimized-os/docs/how-to/create-configure-instance

      <details>
      <summary>alias on cos</summary>

```.bashrc
alias docker-compose='docker run --rm -it \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$PWD:$PWD" \
    -w="$PWD" \
    docker/compose:1.29.2 '

alias gsutil='docker run --rm -it \
    -v $(pwd):$(pwd) \
    -v $HOME:$HOME \
    -v /etc/passwd:/etc/passwd:ro \
    -v /etc/group:/etc/group:ro \
    -v /mnt:/mnt \
    -w $(pwd) \
    -u $(id -u):$(id -g) \
    google/cloud-sdk:latest gsutil "$@" ;'


alias gcsfuse='docker run --rm -it \
    -v $(pwd):$(pwd) \
    -v $HOME:$HOME \
    -v /etc/passwd:/etc/passwd:ro \
    -v /etc/group:/etc/group:ro \
    -v /mnt:/mnt \
    -w $(pwd) \
    -u $(id -u):$(id -g) \
    ningensei848/gcsfuse:latest gcsfuse'
```

</details>

- GCE の _Container-Optimized OS_ で docker を動かす
  - このときに，GCE から GCS バケットをマウントしてやればよい（はず…）
    - マウントするためには `gcsfuse` が必要だが，いまいちうまくいかない
    - 取り敢えず，`gsutil` でコピーしてくることに

Bulk insert に時間がかかることはわかったので，ファイルを一つにまとめるのではなく，複数ファイルで並行してすすめるのが良さそう．
また，そのほうがたくさんのチェックポイントを踏むことになる（頻繁にデータ更新されてコケても損害が小さくて済む）．

virtuoso が稼働している状態で以下のコマンドを実行すると `initialLoader.sql` を読み込んで実行する

`nohup docker exec -i kiai_virtuoso_1 isql 1111 -U dba -P password < ./data/turtle/initialLoader.sql &`

<details>
<summary>prefixies information ... </summary>

#### prefix

```sparql
@prefix netkeiba: <https://db.netkeiba.com/> .
@prefix race: <https://db.netkeiba.com/race/> .

# @prefix tansho: <https://db.netkeiba.com/race/win#> .
# @prefix fukusho: <https://db.netkeiba.com/race/place#> .
# @prefix wakutan: <https://db.netkeiba.com/race/bracket_exacta#> .
# @prefix wakuren: <https://db.netkeiba.com/race/bracket_quinella#> .
# @prefix wide: <https://db.netkeiba.com/race/quinella_place#> .
# @prefix umatan: <https://db.netkeiba.com/race/exacta#> .
# @prefix umaren: <https://db.netkeiba.com/race/quinella#> .
# @prefix sanrenpuku: <https://db.netkeiba.com/race/trio#> .
# @prefix sanrentan: <https://db.netkeiba.com/race/trifecta#> .

@prefix baken: <https://db.netkeiba.com/race/baken/> .
@prefix horse_number: <https://db.netkeiba.com/race/horse_number#> .
@prefix post_position: <https://db.netkeiba.com/race/post_position#> .
```

#### race

- `race:track` : 芝，ダート，障害
- `race:direction` : 右，左，直線，None（※障害）
- `race:distance` : 走行距離
- `race:weather` : 天気
- `race:going` : 地面の状態
- `race:start_at` : 発走時刻
- `race:title` : レースのタイトル
- `race:grade` : レースの格付
- `race:date` : 開催日
- `race:round` : XX 回目の開催
- `race:place` : 開催場所
- `race:days` : XX 日目
- `race:requirement` : 出場要件
- `race:rule` : 参加制限
- `race:dividend` : 配当
  - [] : 空白ノード
    - `baken:type` : 馬券の種別
    - `baken:number` : 的中番号
    - `baken:dividend` : 配当
    - `baken:rank` : 人気
      - （以下同様）
- `race:spacing_on_corner` : spacing_on_corner: コーナーでの配置
  - spacing_on_corner:1 spacing_on_corner:2 spacing_on_corner:3 spacing_on_corner:4
- `race:laptime` : ラップタイム（規定距離ごとの時間）
- `race:pacemaker` : 先頭の通過タイム（累計時間）
- `horse_number:X`: 馬番
- `post_position:X` : 枠番
- `race:finishing_order` : 着順
- `race:runner` : 出走馬一覧

#### horse

```sparql
@prefix netkeiba: <https://db.netkeiba.com/> .
@prefix horse: <https://db.netkeiba.com/horse/> .
@prefix sire: <https://db.netkeiba.com/horse/sire/> .
@prefix bms: <https://db.netkeiba.com/horse/bms/> .

@prefix trainer: <https://db.netkeiba.com/trainer/> .
@prefix owner: <https://db.netkeiba.com/owner/> .
@prefix breeder: <https://db.netkeiba.com/breeder/> .

@prefix relation: <https://db.netkeiba.com/horse/ped#> .
@prefix result: <https://db.netkeiba.com/horse/result#> .
@prefix result_sire: <https://db.netkeiba.com/horse//sire/result#> .
@prefix result_bms: <https://db.netkeiba.com/horse/bms/result#> .
```

- `horse:stallion` : 種牡馬かどうか（Boolean）
- `horse:birthday` : 生年月日
- `horse:trainer` : 調教師
- `horse:owner` : owner: 馬主
- `horse:breeder` :breeder: 生産者
- `horse:country` :country: 産地
- `horse:sale_price` :sale_price: セリ取引価格
- `horse:prize_total` : 総獲得賞金
- `horse:win` : １着
- `horse:second` : ２着
- `horse:third` : ３着
- `horse:lose` : ４着以降
- `horse:race_total` : 総レース数
- `relation:XX` :
  - 父 母 父父 父母 母父 母母 父父父 父父母 父母父 父母母 母父父 母父母 母母父 母母母 父父父父 父父父母 父父母父 父父母母 父母父父 父母父母 父母母父 父母母母 母父父父 母父父母 母父母父 母父母母 母母父父 母母父母 母母母父 母母母母 父父父父父 父父父父母 父父父母父 父父父母母 父父母父父 父父母父母 父父母母父 父父母母母 父母父父父 父母父父母 父母父母父 父母父母母 父母母父父 父母母父母 父母母母父 父母母母母 母父父父父 母父父父母 母父父母父 母父父母母 母父母父父 母父母父母 母父母母父 母父母母母 母母父父父 母母父父母 母母父母父 母母父母母 母母母父父 母母母父母 母母母母父 母母母母母
  - ただし，「父＝`f`」「母＝`m`」で表記
  <!-- cf. https://www.asahi-net.or.jp/~ax2s-kmtn/internet/rdf/rdf-primer.html -->
- `result:RACE_ID`
  - [] : 空白ノード
    - `horse:running`: 参加レース
    - `horse:finishing_order` : 着順
    - `horse:odds` : 単勝
    - `horse:odds_rank` : 人気
    - `horse:sex` : 性別
    - `horse:age` : 年齢
    - `horse:weight` : 体重
    - `horse:gain` : 体重変化(前走比)
    - `horse:impost` : 斤量
    - `horse:racetime` : タイム
    - `horse:margin` : 着差
    - `horse:passing_order` : 通過順位
    - `horse:spurt` : 上り
    - `horse:jockey` : 騎手
    - `horse:trainer`: 調教師
    - `horse:owner` : 馬主
    - `horse:prize_money` : 賞金(万円)

#### sire / bms (horse の特殊例？)

- horse
  - `horse:years_sire`: 種牡馬として活躍した年のリスト
  - `result_sire:YYYY`
    - [] : 空白ノード
      - `sire:rank` : 順位
      - `sire:run_horse` : 出走頭数
      - `sire:win_horse` : 勝馬頭数
      - `sire:run_total` : 出走回数
      - `sire:win_total` : 勝利回数
      - `sire:grade_run` : 重賞/出走
      - `sire:grade_win` : 重賞/勝利
      - `sire:special_run` : 特別/出走
      - `sire:special_win` : 特別/勝利
      - `sire:general_run` : 平場/出走
      - `sire:general_win` : 平場/勝利
      - `sire:turf_run` : 芝/出走
      - `sire:turf_win` : 芝/勝利
      - `sire:dart_run` : ダート/出走
      - `sire:dart_win` : ダート/勝利
      - `sire:win_ratio` : 勝馬率
      - `sire:eanings_index` : EI
      - `sire:prize_total` : 入着賞金(万円)
      - `sire:distance_avg_turf` : 平均距離(芝)
      - `sire:distance_avg_dart` : 平均距離(ダ)
      - `sire:representative` : 代表馬
  - `horse:years_bms`: 種牡馬として活躍した年のリスト
  - `result_bms:YYYY`
    - [] : 空白ノード
      - `bms:rank` : 順位
      - `bms:run_horse` : 出走頭数
      - `bms:win_horse` : 勝馬頭数
      - `bms:run_total` : 出走回数
      - `bms:win_total` : 勝利回数
      - `bms:grade_run` : 重賞/出走
      - `bms:grade_win` : 重賞/勝利
      - `bms:special_run` : 特別/出走
      - `bms:special_win` : 特別/勝利
      - `bms:general_run` : 平場/出走
      - `bms:general_win` : 平場/勝利
      - `bms:turf_run` : 芝/出走
      - `bms:turf_win` : 芝/勝利
      - `bms:dart_run` : ダート/出走
      - `bms:dart_win` : ダート/勝利
      - `bms:win_ratio` : 勝馬率
      - `bms:eanings_index` : EI
      - `bms:prize_total` : 入着賞金(万円)
      - `bms:distance_avg_turf` : 平均距離(芝)
      - `bms:distance_avg_dart` : 平均距離(ダ)
      - `bms:representative` : 代表馬

</details>
