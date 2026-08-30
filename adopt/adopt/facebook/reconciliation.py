import json
import logging
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, TypeVar

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adset import AdSet

from . import field_contract
from .update import Instruction, Provenance

logger = logging.getLogger(__name__)

# What vlab knows about each ad it wants to exist, keyed by the pair that
# identifies an ad within a campaign: (adset name, ad name) -- which is
# (stratum id, creative name). Built purely, upstream, by
# marketing.ad_provenance; consumed here only to stamp create instructions.
ProvenanceLookup = Mapping[Tuple[str, str], Provenance]


def _safe_get(obj, key, default="unknown"):
    """Safely get a field from a Facebook ad object or dict for logging."""
    try:
        return obj[key]
    except (KeyError, TypeError):
        return default


def _declared_drop(path: str) -> bool:
    """True if field_contract says Facebook never echoes `path` back.

    Anything else gets a warning, because an undeclared drop is what an
    endless rewrite loop looks like on its first run: we send a field,
    Facebook omits it from the response, we see a difference, we write again.
    That loop ran ~360 no-op ad writes a day against one ad account until
    2026-07-30 and helped trigger `code 17` throttling.

    See planning/field-contract.md for why tolerance has to be declared per
    field rather than inferred.
    """
    if field_contract.is_dropped(path):
        logger.debug(f"_eq: declared drop at {path} — not compared")
        return True

    logger.warning(
        f"_eq: undeclared drop at {path} — we set this field but Facebook did "
        "not return it. Check with `adopt-probe <study>` and declare it in "
        "field_contract.DROPPED (or stop sending it)."
    )
    return False


def _sort_key(x):
    """Stable sort key for any JSON-serialisable value (dicts, lists, scalars)."""
    return json.dumps(x, sort_keys=True, default=str)


def _eq(a, b, fields=None, _path="", _subset=None) -> bool:
    try:
        a, b = a.export_all_data(), b.export_all_data()
    except AttributeError:
        pass

    # Facebook returns some fields in a different representation than we send
    # (daily_budget as a string, end_time as a tz-offset ISO string). Without
    # this, those compare unequal on every run and the object is rewritten
    # forever even when nothing changed. See field_contract.NORMALIZE.
    normalize = field_contract.normalizer_for(_path)
    if normalize is not None:
        try:
            a, b = normalize(a), normalize(b)
        except (TypeError, ValueError):
            logger.warning(
                f"_eq: normaliser for {_path} could not handle "
                f"{a!r} / {b!r} — comparing raw values"
            )

    # Lists: sort for order-independent comparison, then compare element-by-
    # element with _subset="both" (intersection mode) so that list elements
    # like audience refs {id, name} are compared only on keys both sides
    # have — Facebook may add or strip metadata (e.g. audience name) from
    # list entries without it being a meaningful targeting change.
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            logger.info(
                f"_eq: list length mismatch at {_path} — "
                f"desired={len(a)} source={len(b)}"
            )
            return False
        a_sorted = sorted(a, key=_sort_key)
        b_sorted = sorted(b, key=_sort_key)
        for i, (x, y) in enumerate(zip(a_sorted, b_sorted)):
            if not _eq(x, y, _path=f"{_path}[{i}]", _subset="both"):
                logger.info(
                    f"_eq: mismatch at {_path}[{i}] — "
                    f"desired={x!r} source={y!r}"
                )
                return False
        return True

    try:
        # When a field list is provided, we compare only those fields and
        # tolerate extra keys in either object. This is the top-level behavior
        # used by update_adset/update_ad: existing Facebook objects often
        # contain server-generated fields (id, thumbnail_url, etc.) that we
        # do not set, and we do not want those to force unnecessary updates.
        #
        # The subset comparison propagates to all nested recursion via
        # _subset="a", so that nested structures (e.g. degrees_of_freedom_spec.
        # creative_features_spec, object_story_spec.link_data) also ignore
        # server-generated keys that exist only in the source. Without this
        # propagation, nested comparisons fall into strict symmetric mode and
        # Facebook's ~70 default OPT_OUT creative_features_spec keys cause
        # every ad to be flagged as "creative mismatch" — recreating ads
        # unnecessarily on every run.
        if fields is not None:
            for k, v in a.items():
                if k not in fields:
                    continue
                if k not in b:
                    # Top level stays lenient, as it always has: a whole field
                    # absent from Facebook's response is not something we can
                    # act on, and treating it as a difference would rewrite
                    # the object every run. Still worth a warning if it is not
                    # a drop we already know about.
                    _declared_drop(f"{_path}.{k}")
                    continue
                if not _eq(v, b[k], _path=f"{_path}.{k}", _subset="a"):
                    logger.info(
                        f"_eq: mismatch at {_path}.{k} — "
                        f"desired={v!r} source={b[k]!r}"
                    )
                    return False
            return True

        # Subset mode (nested recursion from a field-list call):
        # Compare only keys present in the desired object (a).  Extra keys
        # in the source (b) — server-generated defaults — are ignored.
        # A key in desired that is missing from source IS a difference, unless
        # it is declared in field_contract.DROPPED.  It has to work this way:
        # a real change (photo_data -> link_data) is indistinguishable in the
        # data from a field Facebook silently drops, so only a declaration can
        # tell them apart.  See _declared_drop.
        if _subset == "a":
            for k, v in a.items():
                if k not in b:
                    # Asking for nothing and being shown nothing is agreement.
                    # Facebook elides empty values rather than echoing them:
                    # targeting.custom_audiences is always set (to [] when the
                    # study has no audiences) and never comes back. Requesting
                    # something non-empty and not seeing it is still a
                    # difference, so adding an audience is not swallowed here.
                    if not v:
                        logger.debug(
                            f"_eq: {_path}.{k} is empty and absent from source "
                            "— treated as equal"
                        )
                        continue
                    if _declared_drop(f"{_path}.{k}"):
                        continue
                    return False
                if not _eq(v, b[k], _path=f"{_path}.{k}", _subset="a"):
                    logger.info(
                        f"_eq: mismatch at {_path}.{k} — "
                        f"desired={v!r} source={b[k]!r}"
                    )
                    return False
            return True

        # Intersection mode (list element comparison):
        # Only compare keys present in BOTH objects.  Used for list elements
        # where Facebook may add or strip metadata fields (e.g. audience
        # name in excluded_custom_audiences) without it being a meaningful
        # change.  The id field is the meaningful identifier.
        if _subset == "both":
            for k in set(a.keys()) & set(b.keys()):
                if not _eq(a[k], b[k], _path=f"{_path}.{k}", _subset="both"):
                    logger.info(
                        f"_eq: mismatch at {_path}.{k} — "
                        f"desired={a[k]!r} source={b[k]!r}"
                    )
                    return False
            return True

        # Strict symmetric mode (standalone calls without a field list).
        # Used for detecting structural changes like link_data vs photo_data
        # in object_story_spec.  Key sets must match exactly.
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


def _check_destination_type_is_still_reachable(source: AdSet, adset: AdSet) -> None:
    """Refuse to build ads into an ad set whose channel no longer matches.

    `destination_type` is deliberately absent from COMPARED_ADSET: it rides
    only on ad-set creates, so a running study cannot change channel underneath
    its own ads. That guard is correct and stays. What was missing was anyone
    saying so when it bites.

    Measured on `vl-pulse-nigeria-smoke`, 2026-08-30. Its ad set was created
    MESSENGER. The study was then pointed at a multi destination, so adopt
    began building multi creatives -- carrying a WhatsApp call-to-action --
    into the ad set Meta still labels MESSENGER. Meta refused every ad with
    "Inconsistent Campaign Destination Type With App Destination" (subcode
    2490279), an error naming neither the ad set nor the study conf, on a run
    that had no other symptom. Hours went into it.

    So: fail here, name both values, and name the remedy. Deleting the ad set
    is the remedy because reconciliation matches ad sets by name and the name
    is the stratum id -- a deleted one is simply recreated, with the derived
    type, on the next run.
    """
    live = _safe_get(source, "destination_type")
    desired = _safe_get(adset, "destination_type")

    if not live or not desired or live == desired:
        return

    name = _safe_get(adset, "name")
    raise Exception(
        f"Ad set '{name}' (id={_safe_get(source, 'id')}) exists on Meta with "
        f"destination_type '{live}', but this study's destinations now imply "
        f"'{desired}'. destination_type cannot be updated on a live ad set — it "
        "is set at create time only — so every ad built into this one would "
        "advertise a channel the ad set does not open, and Meta would refuse "
        f"it. Delete ad set {_safe_get(source, 'id')} in Ads Manager; "
        "reconciliation matches ad sets by name, so it will be recreated with "
        f"'{desired}' on the next run."
    )


def update_adset(source: AdSet, adset: AdSet) -> List[Instruction]:
    # Before anything else: a channel change cannot be applied by update, and
    # proceeding produces ads Meta refuses with an error naming nothing useful.
    _check_destination_type_is_still_reachable(source, adset)

    # Declared, with rationale, in field_contract.COMPARED_ADSET.
    fields = list(field_contract.COMPARED_ADSET)

    # (desired, live), the same order as update_ad. _eq treats its first
    # argument as the authority — everything in it must match the second, and
    # extras in the second are ignored. Facebook adds server-side defaults we
    # never set, so the desired object has to come first. This used to be
    # reversed here, which asked "is everything Facebook returned present in
    # what we want?" — a different question, and the wrong one.
    if _eq(adset, source, fields):
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

    # Declared, with rationale, in field_contract.COMPARED_AD.
    fields = list(field_contract.COMPARED_AD)

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
    provenance: Optional[ProvenanceLookup] = None,
) -> List[Instruction]:
    def provenance_for(x) -> Optional[Provenance]:
        # Stays a pure lookup into data the caller supplied. No database, no
        # Graph API: the write that needs this happens in run_instructions,
        # after Facebook has answered with an id.
        if not provenance:
            return None

        key = (adset["name"], x["name"])
        prov = provenance.get(key)
        if prov is None:
            # Loud, because an ad created without provenance can never be
            # attributed: there is no backfill path, and the respondents it
            # recruits would be silently dropped from every stratum count.
            logger.warning(
                f"ad_dif: creating ad {key} with no provenance — it will not "
                "get an ad_attributions row and its respondents will not be "
                "attributable."
            )
        return prov

    def creator(x):
        params = {**x.export_all_data(), "adset_id": adset["id"]}
        return [Instruction("ad", "create", params, None, provenance_for(x))]

    return _diff("ad", update_ad, creator, old_ads, new_ads)


def adset_dif(
    old_adsets: Sequence[Tuple[AdSet, Sequence[Ad]]],
    new_adsets: Sequence[Tuple[AdSet, Sequence[Ad]]],
    provenance: Optional[ProvenanceLookup] = None,
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
            source, old_lookup[source["name"]], new_lookup[adset["name"]], provenance
        )
        return instructions

    creator = lambda x: [Instruction("adset", "create", x.export_all_data(), None)]

    olds, news = [[a for a, _ in x] for x in [old_adsets, new_adsets]]

    return _diff("adset", updater, creator, olds, news)
