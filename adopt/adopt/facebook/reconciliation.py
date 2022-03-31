from typing import Dict, List, Sequence, Tuple, TypeVar

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adset import AdSet

from .update import Instruction


def _eq(a, b, fields=None) -> bool:
    try:
        a, b = a.export_all_data(), b.export_all_data()
    except AttributeError:
        pass

    try:
        for k, v in a.items():
            if fields and k not in fields:
                continue
            if k not in b:
                continue
            if not _eq(v, b[k]):
                return False
        return True

    except AttributeError:
        return a == b


def update_adset(source: AdSet, adset: AdSet) -> List[Instruction]:
    fields = [
        AdSet.Field.end_time,
        AdSet.Field.targeting,
        AdSet.Field.status,
        AdSet.Field.daily_budget,
        AdSet.Field.optimization_goal,
    ]

    if _eq(source, adset, fields):
        return []

    dat = adset.export_all_data()
    params = {f: dat[f] for f in fields}
    return [Instruction("adset", "update", params, source["id"])]


def update_ad(source: Ad, ad: Ad) -> List[Instruction]:

    if not _eq(ad["creative"], source["creative"]):
        return [Instruction("ad", "update", ad.export_all_data(), source["id"])]

    elif source["status"] != ad["status"]:
        return [Instruction("ad", "update", {"status": ad["status"]}, source["id"])]

    return []


T = TypeVar("T", AdSet, Ad)


def _dedup_olds(type_: str, li: Sequence[T]) -> Tuple[Dict[str, T], List[Instruction]]:

    lookup = {}
    instructions = []

    for obj in li:
        if obj["name"] in lookup:
            instructions += [Instruction(type_, "delete", {}, obj["id"])]
        else:
            lookup[obj["name"]] = obj

    return lookup, instructions


def _diff(type_, updater, creator, olds, news) -> List[Instruction]:
    try:
        old_lookup, instructions = _dedup_olds(type_, olds)
    except KeyError as e:
        raise Exception("Old ad(set)s do not have name!") from e

    updated = set()

    for x in news:
        if x["name"] in old_lookup:
            updated.add(x["name"])
            instructions += updater(old_lookup[x["name"]], x)
        else:
            instructions += creator(x)

    for x in olds:
        if x["name"] not in updated:
            instructions += [Instruction(type_, "delete", {}, x["id"])]

    return instructions


def ad_dif(
    adset: AdSet,
    old_ads: Sequence[Ad],
    new_ads: Sequence[Ad],
) -> List[Instruction]:
    def creator(x):
        params = {**x.export_all_data(), "adset_id": adset["id"]}
        return [Instruction("ad", "create", params, None)]

    return _diff("ad", update_ad, creator, old_ads, new_ads)


def adset_dif(
    old_adsets: Sequence[Tuple[AdSet, Sequence[Ad]]],
    new_adsets: Sequence[Tuple[AdSet, Sequence[Ad]]],
) -> List[Instruction]:

    new_lookup = {a["name"]: ads for a, ads in new_adsets}
    old_lookup = {a["name"]: ads for a, ads in old_adsets}

    def updater(source, adset):
        instructions = update_adset(source, adset)
        instructions += ad_dif(
            source, old_lookup[source["name"]], new_lookup[adset["name"]]
        )
        return instructions

    creator = lambda x: [Instruction("adset", "create", x.export_all_data(), None)]

    olds, news = [[a for a, _ in x] for x in [old_adsets, new_adsets]]

    return _diff("adset", updater, creator, olds, news)
