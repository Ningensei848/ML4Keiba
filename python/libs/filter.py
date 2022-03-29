from typing import List

from libs.path import getHorsePath


def filteringDuplicated(horse_list: List[str]) -> List[str]:

    unregistered_horse_id = [horse_id for horse_id in horse_list if not getHorsePath(horse_id).exists()]
    return unregistered_horse_id
