# ML4Keiba: Machine Learning for `競馬` Dataset

## TL; DR

- Scraping from [netkeiba.com](https://www.netkeiba.com/)
  - complete:  2019 ~
  - on going: 1957 ~ 2018
- (TODO) Convert [`JSON-LD`](https://json-ld.org/)
- (TODO) Deploy to [triple server](https://en.wikipedia.org/wiki/Triplestore) (e.g. Amazon Neptune, Openlink Virtuoso, etc.)

## Example

<details>
<summary>read more ... （第161回天皇賞(春)(G1)）</summary>

```json
{
    "title": "第161回天皇賞(春)(G1)",
    "outer_loop": true,
    "field": "芝",
    "direction": "右",
    "distance": "3200",
    "weather": "曇",
    "going": "良",
    "start_at": "15:40",
    "date": "2020年5月3日",
    "course_info": "3回京都4日目",
    "requirements": "4歳以上オープン",
    "rule": "(国際)(指)(定量)",
    "runner_list": [
        "フィエールマン",
        "スティッフェリオ",
        "ミッキースワロー",
        "ユーキャンスマイル",
        "トーセンカンビーナ",
        "キセキ",
        "モズベッロ",
        "メイショウテンゲン",
        "ダンビュライト",
        "エタリオウ",
        "メロディーレーン",
        "ミライヘノツバサ",
        "ハッピーグリン",
        "シルヴァンシャー"
    ],
    "runner": {
        "フィエールマン": {
            "horce_id": "2015105075",
            "horse_name": "フィエールマン",
            "jockey_id": "05339",
            "jockey_name": "ルメール",
            "trainer_id": "01038",
            "trainer_name": "手塚貴久",
            "trainer_org": "東",
            "owner_id": "226800",
            "owner_name": "サンデーレーシング"
        },
        "スティッフェリオ": {
            "horce_id": "2014105517",
            "horse_name": "スティッフェリオ",
            "jockey_id": "01102",
            "jockey_name": "北村友一",
            "trainer_id": "01002",
            "trainer_name": "音無秀孝",
            "trainer_org": "西",
            "owner_id": "415800",
            "owner_name": "社台レースホース"
        },
        "ミッキースワロー": {
            "horce_id": "2014106160",
            "horse_name": "ミッキースワロー",
            "jockey_id": "00660",
            "jockey_name": "横山典弘",
            "trainer_id": "01115",
            "trainer_name": "菊沢隆徳",
            "trainer_org": "東",
            "owner_id": "441007",
            "owner_name": "野田みづき"
        },
        "ユーキャンスマイル": {
            "horce_id": "2015105032",
            "horse_name": "ユーキャンスマイル",
            "jockey_id": "01115",
            "jockey_name": "浜中俊",
            "trainer_id": "01061",
            "trainer_name": "友道康夫",
            "trainer_org": "西",
            "owner_id": "708800",
            "owner_name": "金子真人ホールディングス"
        },
        "トーセンカンビーナ": {
            "horce_id": "2016104990",
            "horse_name": "トーセンカンビーナ",
            "jockey_id": "01116",
            "jockey_name": "藤岡康太",
            "trainer_id": "01053",
            "trainer_name": "角居勝彦",
            "trainer_org": "西",
            "owner_id": "270006",
            "owner_name": "島川隆哉"
        },
        "キセキ": {
            "horce_id": "2014101976",
            "horse_name": "キセキ",
            "jockey_id": "00666",
            "jockey_name": "武豊",
            "trainer_id": "01053",
            "trainer_name": "角居勝彦",
            "trainer_org": "西",
            "owner_id": "248030",
            "owner_name": "石川達絵"
        },
        "モズベッロ": {
            "horce_id": "2016100915",
            "horse_name": "モズベッロ",
            "jockey_id": "01032",
            "jockey_name": "池添謙一",
            "trainer_id": "01142",
            "trainer_name": "森田直行",
            "trainer_org": "西",
            "owner_id": "005803",
            "owner_name": "キャピタル・システム"
        },
        "メイショウテンゲン": {
            "horce_id": "2016102192",
            "horse_name": "メイショウテンゲン",
            "jockey_id": "00732",
            "jockey_name": "幸英明",
            "trainer_id": "01021",
            "trainer_name": "池添兼雄",
            "trainer_org": "西",
            "owner_id": "523005",
            "owner_name": "松本好雄"
        },
        "ダンビュライト": {
            "horce_id": "2014106010",
            "horse_name": "ダンビュライト",
            "jockey_id": "01154",
            "jockey_name": "松若風馬",
            "trainer_id": "01002",
            "trainer_name": "音無秀孝",
            "trainer_org": "西",
            "owner_id": "226800",
            "owner_name": "サンデーレーシング"
        },
        "エタリオウ": {
            "horce_id": "2015104995",
            "horse_name": "エタリオウ",
            "jockey_id": "01088",
            "jockey_name": "川田将雅",
            "trainer_id": "01061",
            "trainer_name": "友道康夫",
            "trainer_org": "西",
            "owner_id": "098803",
            "owner_name": "Ｇリビエール・レーシング"
        },
        "メロディーレーン": {
            "horce_id": "2016105526",
            "horse_name": "メロディーレーン",
            "jockey_id": "01174",
            "jockey_name": "岩田望来",
            "trainer_id": "01142",
            "trainer_name": "森田直行",
            "trainer_org": "西",
            "owner_id": "851009",
            "owner_name": "岡田牧雄"
        },
        "ミライヘノツバサ": {
            "horce_id": "2013109072",
            "horse_name": "ミライヘノツバサ",
            "jockey_id": "01162",
            "jockey_name": "木幡巧也",
            "trainer_id": "01109",
            "trainer_name": "伊藤大士",
            "trainer_org": "東",
            "owner_id": "672030",
            "owner_name": "三島宣彦"
        },
        "ハッピーグリン": {
            "horce_id": "2015104624",
            "horse_name": "ハッピーグリン",
            "jockey_id": "01018",
            "jockey_name": "和田竜二",
            "trainer_id": "00427",
            "trainer_name": "森秀行",
            "trainer_org": "西",
            "owner_id": "131031",
            "owner_name": "会田裕一"
        },
        "シルヴァンシャー": {
            "horce_id": "2015104649",
            "horse_name": "シルヴァンシャー",
            "jockey_id": "05212",
            "jockey_name": "Ｍ．デム",
            "trainer_id": "01071",
            "trainer_name": "池江泰寿",
            "trainer_org": "西",
            "owner_id": "226800",
            "owner_name": "サンデーレーシング"
        }
    },
    "ticket_types": [
        "win",
        "place",
        "bracket_quinella",
        "quinella",
        "quinella_place",
        "exacta",
        "trio",
        "tierce"
    ],
    "dividend": {
        "win": {
            "ja-JP": "単勝",
            "official": "14",
            "refund": "200",
            "favorite": "1"
        },
        "place": {
            "ja-JP": "複勝",
            "official": "14/6/5",
            "refund": "130/830/290",
            "favorite": "1/10/4"
        },
        "bracket_quinella": {
            "ja-JP": "枠連",
            "official": "4 - 8",
            "refund": "1110",
            "favorite": "4"
        },
        "quinella": {
            "ja-JP": "馬連",
            "official": "6 - 14",
            "refund": "5770",
            "favorite": "20"
        },
        "quinella_place": {
            "ja-JP": "ワイド",
            "official": "6 - 14/5 - 14/5 - 6",
            "refund": "1,790/510/5,160",
            "favorite": "22/3/45"
        },
        "exacta": {
            "ja-JP": "馬単",
            "official": "14 → 6",
            "refund": "7410",
            "favorite": "25"
        },
        "trio": {
            "ja-JP": "三連複",
            "official": "5 - 6 - 14",
            "refund": "13500",
            "favorite": "44"
        },
        "tierce": {
            "ja-JP": "三連単",
            "official": "14 → 6 → 5",
            "refund": "55200",
            "favorite": "186"
        }
    },
    "order_of_corner": [
        "8-4-6,1,13(7,12)14(2,5)9,11,10-3",
        "8-4-61137121425911103",
        "8-4-6-1(5,11)(7,13,14,3)2(12,9)10",
        "8-4-6(1,5)7,14(11,3)-2,9,10,12,13"
    ],
    "racetime": {
        "ラップ": "13.2 - 12.4 - 12.4 - 12.5 - 12.5 - 12.0 - 11.6 - 12.5 - 12.1 - 12.2 - 12.7 - 12.5 - 11.9 - 11.9 - 11.9 - 12.2",
        "ペース": "13.2 - 25.6 - 38.0 - 50.5 - 63.0 - 75.0 - 86.6 - 99.1 - 111.2 - 123.4 - 136.1 - 148.6 - 160.5 - 172.4 - 184.3 - 196.5 (38.0-36.0)"
    }
}
```

</details>

## (TODO) Schema

underconstruction
