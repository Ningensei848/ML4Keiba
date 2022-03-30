from typing import List

from libs.path import getHorsePath


def pathExist(horse_id: str) -> bool:
    if not horse_id:
        return False

    filepath = getHorsePath(horse_id)

    if filepath:
        return filepath.exists()
    else:
        return False


def filteringDuplicated(horse_list: List[str]) -> List[str]:

    unregistered_horse_id = [horse_id for horse_id in horse_list if pathExist(horse_id)]
    return unregistered_horse_id
