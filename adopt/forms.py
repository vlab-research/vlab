import re
import json
import warnings

import yaml
import pystache

def grep_label(text, label):
    r = '\n-? ?' + label + r'.? ([^\n]+)'
    finds = re.findall(r, text)
    if len(finds) != 1:
        raise Exception('Could not create label from paragraph!')
    return finds[0]

def multiple_choice(q):
    labels = [c['label'] for c in q['properties']['choices']]
    if labels[0] == 'A':
        return [(l, grep_label(q['title'], l)) for l in labels]
    return [(l,l) for l in labels]

def notify(q):
    # TODO: this is language-specific and comes from FB!
    labels = [('Notify Me', 'Notify Me')]
    return labels

def get_type(q):
    try:
        desc = q['properties']['description']
        desc = pystache.render(desc, {})
        parsed = yaml.safe_load(desc)
        return parsed['type']
    except AttributeError:
        return q['type']
    except KeyError:
        return q['type']


class FunctionDict():
    def __init__(self, fn):
        self.fn = fn

    def __getitem__(self, k):
        return self.fn(k)

    def __setitem__(self, k, v):
        raise AttributeError('Cannot set items to function dict!')


class TranslationError(BaseException):
    pass

def identity(q):
    return lambda x: x

def make_answers(q):
    types = {
        'notify': notify,
        'multiple_choice': multiple_choice,
        'opinion_scale': multiple_choice,
        'rating': multiple_choice,
        # legal, yes/no????
    }

    others = ['number', 'short_text', 'email', 'phone_number', 'long_text']
    statements = ['statement', 'attachment', 'stitch', 'wait', 'webview', 'thankyou_screen', 'welcome_screen']
    types = {**types, **{k: identity for k in others + statements}}

    type_ = get_type(q)
    try:
        return types[type_](q)
    except KeyError:
        raise Exception(f'I dunno what to do with this type yet! {type_}')


def response_translator(q, qt=None):
    if not qt:
        qt = q

    ta = get_type(q)
    tb = get_type(qt)
    if ta != tb:
        raise TranslationError(f'Cannot translate. Questions with refs {q["ref"]} and '
                               f'{qt["ref"]} across forms have different types: {ta} and {tb}')

    try:
        lookup = {res: vt for (res, _), (_, vt)
                  in zip(make_answers(q), make_answers(qt))}
    except TypeError:
        lookup = make_answers(q)

    def _translator(r):
        try:
            return lookup[r]
        except TypeError:
            return lookup(r)
        except KeyError as e:
            return None

    return _translator


def translate_response(translators, surveyid, q_ref, response):
    try:
        t = translators[surveyid]
    except KeyError as e:
        raise TranslationError('Cannot find survey with surveyid: {surveyid}') from e

    try:
        t = t[q_ref]
    except KeyError as e:
        raise TranslationError('Cannot find question ref {q_ref} in survey {surveyid}') from e

    return t(response)


# TODO: change the zip to something that checks refs???
# or add warning if refs aren't equal??
def _make_translators(ref_form, other_form):
    fields = list(zip(ref_form['fields'], other_form['fields']))

    for a, b in fields:
        if (ar := a['ref']) != (br := b['ref']):
            warnings.warn(f'Forms have differently refd fields: {ar} and {br}')

    return { b['ref']: response_translator(b, a)
             for a, b in fields }


def make_translators(forms):
    ts = [{ form['id']: _make_translators(ref_form['form_json'],
                                          form['form_json'])
            for form in other_forms }
          for ref_form, other_forms in forms]

    d = {}
    for t in ts:
        d = {**d, **t}
    return d


def _get_ref(forms, field, ref):
    ref_forms = [f for f in forms
                 if f['metadata'][field] == ref]

    try:
        latest = sorted(ref_forms, key=lambda f: f['created'])[-1]
    except IndexError as e:
        raise TranslationError(f'Could not find reference form from forms with metadatas {[f["metadata"] for f in forms]}') from e

    return latest

def org_translators(forms, conf):
    field = conf['field']

    d = {}
    for f in forms:
        md = f['metadata']
        key = frozenset([(k,v) for k, v in md.items()
                          if k != field])
        try:
            d[key] += [f]
        except KeyError:
            d[key] = [f]

    return [(_get_ref(fs, field, conf['reference']), fs)
            for fs in d.values()]


def translators_for_survey(forms, conf):
    return make_translators(org_translators(forms, conf))
