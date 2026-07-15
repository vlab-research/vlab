import logging
from typing import Dict, List, Sequence, Tuple, TypeVar

from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adset import AdSet

from .update import Instruction

logger = logging.getLogger(__name__)


def _safe_get(obj, key, default="unknown"):
    """Safely get a field from a Facebook ad object or dict for logging."""
    try:
        return obj[key]
    except (KeyError, TypeError):
        return default


def _eq(a, b, fields=None, _path="") -> bool:
    try:
        a, b = a.export_all_data(), b.export_all_data()
    except AttributeError:
        pass

    try:
        # When a field list is provided, we compare only those fields and
        # tolerate extra keys in either object. This is the top-level behavior
        # used by update_adset/update_ad: existing Facebook objects often
        # contain server-generated fields (id, thumbnail_url, etc.) that we
        # do not set, and we do not want those to force unnecessary updates.
        if fields is not None:
            for k, v in a.items():
                if k not in fields:
                    continue
                if k not in b:
                    logger.debug(
                        f"_eq: field '{k}' present in desired but missing from "
                        f"source (path: {_path}.{k}) — skipping"
                    )
                    continue
                if not _eq(v, b[k], _path=f"{_path}.{k}"):
                    logger.info(
                        f"_eq: mismatch at {_path}.{k} — "
                        f"desired={v!r} source={b[k]!r}"
                    )
                    return False
            return True

        # When no field list is provided, we do a strict symmetric comparison.
        # This is used for nested structures like object_story_spec, where a
        # difference in keys (e.g. desired has link_data while existing has
        # photo_data) must be detected so the optimizer can update the creative.
        #
        # BUG: this strict mode is also reached when the top-level call
        # (which *does* pass a field list) recurses into nested values
        # (line: _eq(v, b[k]) — no fields arg).  Live Facebook data has
        # server-generated keys in nested structures (e.g. link_data gets
        # extra keys from the API) that the desired creative does not have,
        # causing the key-set check below to fail and declare identical
        # creatives as different.
        if set(a.keys()) != set(b.keys()):
            only_desired = set(a.keys()) - set(b.keys())
            only_source = set(b.keys()) - set(a.keys())
            logger.info(
                f"_eq: key-set mismatch at {_path} — "
                f"keys only in desired: {only_desired} | "
                f"keys only in source: {only_source}"
            )
            return False

        for k, v in a.items():
            if not _eq(v, b[k], _path=f"{_path}.{k}"):
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
        AdSet.Field.name,
    ]

    if _eq(source, adset, fields):
        logger.debug(
            f"update_adset: no-op for adset '{_safe_get(adset, 'name')}' "
            f"(id={_safe_get(source, 'id')})"
        )
        return []

    logger.info(
        f"update_adset: generating update for adset '{_safe_get(adset, 'name')}' "
        f"(id={_safe_get(source, 'id')})"
    )
    dat = adset.export_all_data()
    params = {f: dat[f] for f in fields}
    return [Instruction("adset", "update", params, source["id"])]


def update_ad(source: Ad, ad: Ad) -> List[Instruction]:

    fields = [
        AdCreative.Field.actor_id,
        AdCreative.Field.image_crops,
        AdCreative.Field.asset_feed_spec,
        AdCreative.Field.degrees_of_freedom_spec,
        AdCreative.Field.instagram_user_id,
        AdCreative.Field.object_story_spec,
        AdCreative.Field.contextual_multi_ads,
        AdCreative.Field.thumbnail_url,
        AdCreative.Field.url_tags,
    ]

    if not _eq(ad["creative"], source["creative"], fields):
        logger.warning(
            f"update_ad: creative mismatch for ad '{_safe_get(ad, 'name')}' "
            f"(id={_safe_get(source, 'id')}) — generating full ad update"
        )
        return [Instruction("ad", "update", ad.export_all_data(), source["id"])]

    elif source["status"] != ad["status"]:
        logger.info(
            f"update_ad: status change for ad '{_safe_get(ad, 'name')}' "
            f"(id={_safe_get(source, 'id')}) — "
            f"{source['status']} -> {ad['status']}"
        )
        return [Instruction("ad", "update", {"status": ad["status"]}, source["id"])]

    logger.debug(
        f"update_ad: no-op for ad '{_safe_get(ad, 'name')}' "
        f"(id={_safe_get(source, 'id')})"
    )
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
            logger.debug(
                f"_diff: {type_} '{x['name']}' matched existing — calling updater"
            )
            instructions += updater(old_lookup[x["name"]], x)
        else:
            logger.info(
                f"_diff: {type_} '{x['name']}' not found in existing — creating"
            )
            instructions += creator(x)

    for x in olds:
        if x["name"] not in updated:
            logger.info(
                f"_diff: {type_} '{x['name']}' no longer in desired — deleting "
                f"(id={x['id']})"
            )
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

    old_names = set(old_lookup.keys())
    new_names = set(new_lookup.keys())
    logger.info(
        f"adset_dif: {len(old_adsets)} existing adset(s) vs {len(new_adsets)} desired "
        f"— matched: {old_names & new_names} | "
        f"to create: {new_names - old_names} | "
        f"to delete: {old_names - new_names}"
    )

    def updater(source, adset):
        instructions = update_adset(source, adset)
        instructions += ad_dif(
            source, old_lookup[source["name"]], new_lookup[adset["name"]]
        )
        return instructions

    creator = lambda x: [Instruction("adset", "create", x.export_all_data(), None)]

    olds, news = [[a for a, _ in x] for x in [old_adsets, new_adsets]]

    return _diff("adset", updater, creator, olds, news)
