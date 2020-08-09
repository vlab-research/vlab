import re
import yaml

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
        parsed = yaml.safe_load(q['properties'].get('description'))
        return parsed['type']
    except AttributeError:
        return q['type']


def make_answers(q):
    types = {
        'multiple_choice': multiple_choice,
        'notify': notify
    }

    type_ = get_type(q)
    try:
        return types[type_](q)
    except KeyError:
        raise Exception(f'I dunno what to do with this type yet! {type_}')

class BadResponseError(BaseException):
    pass

def response_translator(q, qt=None):
    if not qt:
        qt = q

    lookup = {res: vt for (res, _), (_, vt)
              in zip(make_answers(q), make_answers(qt))}

    def _translator(r):
        try:
            return lookup[r]
        except KeyError:
            raise BadResponseError(f'Response not mapped to label: {r}')

    return _translator
