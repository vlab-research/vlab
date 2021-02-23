from functools import lru_cache

import requests
from toolz import groupby

from adopt.forms import TranslationError
from adopt.responses import query

from .variables import variable_lookup


def temp_translation_target(surveyid, cnf):
    q = """
    WITH t AS
      (SELECT created,
              survey_name,
              form_json,
              translation_conf,
              jsonb_set(metadata,
                        ARRAY['language'],
                        '"english"') AS ref_metadata
       FROM surveys
       WHERE id = %s
       LIMIT 1)
    SELECT surveys.id AS dest,
           surveys.shortcode AS shortcode,
           surveys.form_json as dest_form, t.form_json as form_json
    FROM t
    LEFT JOIN surveys
    ON t.survey_name = surveys.survey_name
    AND t.ref_metadata = surveys.metadata
    ORDER BY surveys.created
    LIMIT 1
    """

    res = query(dict(cnf), q, (surveyid,), as_dict=True)
    return next(res)


def try_trans(g, shortcode, fn):
    for s in g[shortcode]:
        res = fn(s)
        if res:
            return res
    raise Exception(f"could not translate into shortcode: {shortcode}")


def get_translator(formcentral_url, g, shortcode, form):
    for s in g[shortcode]:
        body = {"form": form, "destination": s["id"]}
        res = requests.post(f"{formcentral_url}/translators", json=body)
        res = res.json()
        if not res.get("message"):
            res["destination_id"] = s["id"]
            return res

    print(f'ERROR for destination {shortcode}: {res.get("message")}')
    return None


def translate_response(translators, surveyid, q_ref, response):
    try:
        t = translators[surveyid]
    except KeyError as e:
        raise TranslationError(f"Cannot find survey with surveyid: {surveyid}") from e

    if not t:
        return None

    try:
        t = t["fields"][q_ref]
    except KeyError:
        # only happening for hinexc...
        return None
    except TypeError as e:
        raise TranslationError(f"Problem translating survey {surveyid}") from e

    if t["translate"]:
        try:
            return t["mapping"][response]
        except KeyError:
            return None
    else:
        return response


def replace_from(new_key, old_key, fn, li):
    return [{**d, new_key: fn(d.get(old_key))} for d in li]


def translate_responses(db_conf, forms, formcentral_url, responses):
    form_lookup = {f["id"]: f for f in forms}
    g = groupby("shortcode", forms).items()
    g = {k: sorted(v, key=lambda f: f["created"]) for k, v in g}

    replacement_survey = g["baselinehin"][-1]["id"]

    targets = [temp_translation_target(f["id"], db_conf) for f in forms]
    translation_confs = [
        (formcentral_url, g, dest["shortcode"], form["form_json"])
        for form, dest in zip(forms, targets)
    ]
    translators = [get_translator(*tc) for tc in translation_confs]
    translators = {form["id"]: t for t, form in zip(translators, forms)}
    translators = {
        k: v if v is not None else translators[replacement_survey]
        for k, v in translators.items()
    }

    tr = [
        {
            **r,
            "translated_response": translate_response(
                translators, r["surveyid"], r["question_ref"], r["response"]
            ),
        }
        for r in responses
    ]

    excs = {f["id"] for f in g["baselinehinexc"]}
    clean_surveys = lambda sid: replacement_survey if sid in excs else sid
    get_translated_id = lambda s: translators[s]["destination_id"]

    tr = replace_from("surveyid", "surveyid", clean_surveys, tr)
    tr = replace_from("t_surveyid", "surveyid", get_translated_id, tr)

    @lru_cache(100000)
    def lookup_ref(tid, id_, qr):
        dst, src = form_lookup[tid], form_lookup[id_]
        for sf, df in zip(src["form_json"]["fields"], dst["form_json"]["fields"]):
            if sf["ref"] == qr:
                return df["ref"]

    tr = [
        {
            **d,
            "tref": lookup_ref(d["t_surveyid"], d["surveyid"], d["question_ref"]),
        }
        for d in tr
    ]

    tr = replace_from("question_ref", "tref", lambda r: variable_lookup.get(r), tr)

    return tr
