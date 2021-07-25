# ML4Keiba: Machine Learning for `競馬`

On going ... sorry (; _ ;)


## TL; DR

- (TODO) Convert [`JSON-LD`](https://json-ld.org/)
- (TODO) Deploy to [triple server](https://en.wikipedia.org/wiki/Triplestore) (e.g. Amazon Neptune, Openlink Virtuoso, etc.)

## [WIP] Schema (JSON-LD context) 

[check here!](https://raw.githubusercontent.com/Ningensei848/ML4Keiba/main/contexts.jsonld)

<details>
<summary>OR read more ... </summary>

```json
{
  "@context": {
    "@version": 1.1,
    "schema": {
      "@id": "http://schema.org/",
      "@type": "@id"
    },
    "name": {
      "@id": "schema:name",
      "@type": "@id"
    },
    "wd": {
      "@id": "https://www.wikidata.org/entity/",
      "@type": "@id"
    },
    "dcterms": {
      "@id": "http://purl.org/dc/terms/",
      "@type": "@id"
    },
    "netkeiba": {
      "@id": "https://db.netkeiba.com/",
      "@type": "@id"
    },
    "race_id": {
      "@id": "netkeiba:race/",
      "@type": "@id"
    },
    "title": {
      "@id": "dcterms:title",
      "@type": "@id"
    },
    "outer_loop": {
      "@id": "wd:Q7112024",
      "@type": "@id"
    },
    "field": {
      "@id": "wd:Q17116231",
      "@type": "@id"
    },
    "direction": {
      "@id": "wd:Q504111",
      "@type": "@id"
    },
    "distance": {
      "@id": "wd:Q126017",
      "@type": "@id"
    },
    "weather": {
      "@id": "wd:Q11663",
      "@type": "@id"
    },
    "going": {
      "@id": "wd:Q7831528",
      "@type": "@id"
    },
    "start_at": {
      "@id": "wd:Q24575110",
      "@type": "@id"
    },
    "date": {
      "@id": "wd:Q205892",
      "@type": "@id"
    },
    "course_info": {
      "@id": "wd:Q1751609",
      "@type": "@id"
    },
    "requirements": {
      "@id": "wd:Q2122052",
      "@type": "@id"
    },
    "rule": {
      "@id": "wd:Q1151067",
      "@type": "@id"
    },
    "runner": {
      "@id": "wd:Q2442470",
      "@type": "@id",
      "@container": "@list"
    },
    "horce_id": {
      "@id": "netkeiba:horse/",
      "@type": "@id"
    },
    "jockey": {
      "@id": "wd:P5317",
      "@type": "@id"
    },
    "jockey_id": {
      "@id": "netkeiba:jockey/",
      "@type": "@id"
    },
    "trainer": {
      "@id": "wd:Q41583",
      "@type": "@id"
    },
    "trainer_id": {
      "@id": "netkeiba:trainer/",
      "@type": "@id"
    },
    "owner_id": {
      "@id": "netkeiba:owner/",
      "@type": "@id"
    },
    "race": {
      "@id": "dcterms:title",
      "@type": "@id"
    },
    "member_of": {
      "@id": "wdt:P463",
      "@type": "@id"
    },
    "owner": {
      "@id": "wdt:P127",
      "@type": "@id"
    },
    "uniform_number": {
      "@id": "wd:Q599003",
      "@type": "@id"
    },
    "gate_number": {
      "@id": "wd:Q1748673",
      "@type": "@id"
    },
    "organism": {
      "@id": "wd:Q7239",
      "@type": "@id"
    },
    "age": {
      "@id": "wd:Q100343219",
      "@type": "@id"
    },
    "counterweight": {
      "@id": "wd:Q1324102",
      "@type": "@id"
    },
    "racetime": {
      "@id": "wdt:P2781",
      "@type": "@id"
    },
    "race_result": {
      "@id": "wd:Q54933017",
      "@type": "@id"
    },
    "diff_order": {
      "@id": "wd:Q10862449",
      "@type": "@id"
    },
    "rank_at_corner": {
      "@id": "wd:Q526719",
      "@type": "@id",
      "@container": "@list"
    },
    "max_speed": {
      "@id": "wd:Q28809136",
      "@type": "@id"
    },
    "odds": {
      "@id": "wd:Q515895",
      "@type": "@id"
    },
    "odds_rank": {
      "@id": "wd:Q4120621",
      "@type": "@id"
    },
    "body": {
      "@id": "wd:Q170494",
      "@type": "@id"
    },
    "weight": {
      "@id": "wdt:P2067",
      "@type": "@id"
    },
    "gain": {
      "@id": "wd:Q3403879",
      "@type": "@id"
    },
    "bounty": {
      "@id": "wd:Q4372150",
      "@type": "@id"
    },
    "baken": {
      "@id": "https://www.jra.go.jp/kouza/beginner/baken/#type_",
      "@type": "wd:Q181201"
    },
    "dividend": {
      "@id": "wd:Q181201",
      "@type": "wd:Q1506462"
    },
    "official": {
      "@id": "wd:Q29509043",
      "@type": "wd:@id"
    },
    "refund": {
      "@id": "wd:Q28451489",
      "@type": "@id"
    },
    "win": {
      "@id": "baken:tansyo",
      "@type": "wd:Q181201"
    },
    "place": {
      "@id": "baken:fukusyo",
      "@type": "wd:Q181201"
    },
    "bracket_quinella": {
      "@id": "baken:wakuren",
      "@type": "wd:Q181201"
    },
    "exacta": {
      "@id": "baken:umatan",
      "@type": "wd:Q181201"
    },
    "quinella": {
      "@id": "baken:umaren",
      "@type": "wd:Q181201"
    },
    "quinella_place": {
      "@id": "baken:wide",
      "@type": "wd:Q181201"
    },
    "trio": {
      "@id": "baken:3renpuku",
      "@type": "wd:Q181201"
    },
    "tierce": {
      "@id": "baken:3rentan",
      "@type": "wd:Q181201"
    },
    "spacing_on_corner": {
      "@id": "wd:Q56316565",
      "@type": "@id",
      "@container": "@list"
    },
    "lap": {
      "@id": "wd:Q26484625",
      "@type": "@id"
    },
    "pacemaker": {
      "@id": "wd:Q1888395",
      "@type": "@id"
    },
    "movie": {
      "@id": "wd:Q93204",
      "@type": "@id"
    },
    "movie_id": {
      "@id": "netkeiba:race/movie/",
      "@type": "@id"
    }
  }
}
```

</details>
