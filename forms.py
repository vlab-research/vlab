import re

def grep_label(text, label):
    r = '\n-? ?' + label + r'.? ([^\n]+)'
    finds = re.findall(r, text)
    if len(finds) != 1:
        raise Exception('Could not create label from paragraph!')
    return finds[0]


def make_answers(q):
    if q['type'] != 'multiple_choice':
        raise Exception(f'I dunno what to do with this type yet! {q["type"]}')

    labels = [c['label'] for c in q['properties']['choices']]
    if labels[0] == 'A':
        return [(l, grep_label(q['title'], l)) for l in labels]
    return [(l,l) for l in labels]


def response_translator(q, qt=None):
    if not qt:
        qt = q

    lookup = {res: vt for (res, _), (_, vt)
              in zip(make_answers(q), make_answers(qt))}

    def _translator(r):
        try:
            return lookup[r]
        except KeyError:
            raise Exception(f'Response not mapped to label: {r}')

    return _translator
