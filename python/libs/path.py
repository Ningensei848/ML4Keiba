from pathlib import Path

cwd = Path.cwd()


def getHorsePath(horse_id: str, dir="json") -> Path:

    yyyy, xxxx, zz = horse_id[:4], horse_id[4:8], horse_id[8:]
    filepath = cwd / "data" / "horse" / dir / "profile" / yyyy / xxxx / f"{zz}.json"

    return filepath
