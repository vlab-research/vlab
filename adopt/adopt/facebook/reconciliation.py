import re
from typing import Dict, List, Optional, Sequence, Tuple, TypeVar

from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.leadgenform import LeadgenForm

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
        AdSet.Field.name,
    ]

    if _eq(source, adset, fields):
        return []

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


#############################
# Lead Gen Form Reconciliation
#############################


def get_latest_form_version(
    forms: Sequence[LeadgenForm],
    base_name: str,
) -> Optional[Tuple[LeadgenForm, int]]:
    """
    Find the latest version of a form by base name.
    Returns (form, version_number) or None if not found.
    Ignores ARCHIVED and DELETED forms.
    """
    pattern = re.compile(rf"^{re.escape(base_name)}-v(\d+)$")

    matching_forms = []
    for form in forms:
        # Skip archived/deleted
        if form.get("status") in ["ARCHIVED", "DELETED"]:
            continue

        match = pattern.match(form["name"])
        if match:
            version = int(match.group(1))
            matching_forms.append((form, version))

    if not matching_forms:
        return None

    # Return form with highest version
    return max(matching_forms, key=lambda x: x[1])


def _form_needs_update(
    existing_form: LeadgenForm,
    desired_params: Dict[str, any],
) -> bool:
    """
    Check if form needs updating by comparing key fields.
    Returns True if any field differs.
    """
    fields_to_compare = ["questions", "tracking_parameters", "context_card", "thank_you_page"]

    return any(
        not _eq(existing_form.get(field), desired_params.get(field))
        for field in fields_to_compare
    )


def form_dif(
    old_forms: Sequence[LeadgenForm],
    new_form_specs: Sequence[Tuple[str, Dict[str, any]]],
) -> List[Instruction]:
    """
    Compare existing forms with desired form specs.
    Returns Instructions to archive old versions and create new ones as needed.

    Args:
        old_forms: Existing forms from Facebook
        new_form_specs: List of (base_name, params) tuples
    """
    # Import here to avoid circular dependency
    from ..marketing import make_leadgen_form_name

    instructions = []

    for base_name, desired_params in new_form_specs:
        latest = get_latest_form_version(old_forms, base_name)

        if latest is None:
            # Form doesn't exist, create v1
            form_name = make_leadgen_form_name(base_name, 1)
            params = {**desired_params, "name": form_name}
            instructions.append(Instruction("leadgen_form", "create", params, None))

        else:
            existing_form, current_version = latest

            if _form_needs_update(existing_form, desired_params):
                # Archive old version
                archive_params = {"status": "ARCHIVED"}
                instructions.append(
                    Instruction("leadgen_form", "update", archive_params, existing_form["id"])
                )

                # Create new version
                next_version = current_version + 1
                form_name = make_leadgen_form_name(base_name, next_version)
                params = {**desired_params, "name": form_name}
                instructions.append(Instruction("leadgen_form", "create", params, None))

            # else: form exists and matches, no action needed

    return instructions
