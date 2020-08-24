from .forms import *

def test_make_answers_labelled():
    q = {'title': 'What is your gender? ',
         'ref': '20218ad0-96c8-4799-bdfe-90c689c5c206',
         'properties': {
                        'choices': [{'label': 'Male'},
                                    {'label': 'Female'},
                                    {'label': 'Other'}]},
         'type': 'multiple_choice'}

    res = make_answers(q)
    assert res == [('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]



def test_make_answers_to_notify():
    q = {'title': 'What is your gender? ',
         'ref': '20218ad0-96c8-4799-bdfe-90c689c5c206',
         'properties': {
             'description': 'type: notify',
             'choices': [{'label': 'Male'},
                         {'label': 'Female'},
                         {'label': 'Other'}]},
         'type': 'multiple_choice'}

    res = make_answers(q)
    assert res == [('Notify Me', 'Notify Me')]


def test_make_answers_labelled_with_dash():
    q = {'title': 'Which state do you currently live in?\n- A. foo 91  bar\n- B. Jharkhand\n- C. Odisha\n- D. Uttar Pradesh',
         'ref': '20218ad0-96c8-4799-bdfe-90c689c5c206',
         'properties': {
             'choices': [{'label': 'A'},
                         {'label': 'B'},
                         {'label': 'C'},
                         {'label': 'D'}]},
         'type': 'multiple_choice'}

    res = make_answers(q)
    assert res == [('A', 'foo 91  bar'),
                   ('B', 'Jharkhand'),
                   ('C', 'Odisha'),
                   ('D', 'Uttar Pradesh')]

def test_make_answers_labelled_without_dash():
    q = {'title': 'Which state do you currently live in?\nA. foo 91  bar\nB. Jharkhand\nC. Odisha\nD. Uttar Pradesh',
         'ref': '20218ad0-96c8-4799-bdfe-90c689c5c206',
         'properties': {
             'choices': [{'label': 'A'},
                         {'label': 'B'},
                         {'label': 'C'},
                         {'label': 'D'}]},
         'type': 'multiple_choice'}

    res = make_answers(q)
    assert res == [('A', 'foo 91  bar'),
                   ('B', 'Jharkhand'),
                   ('C', 'Odisha'),
                   ('D', 'Uttar Pradesh')]


def test_response_translator_translate_when_other():
    q = {'id': 'vjl6LihKMtcX',
         'title': 'आपका लिंग क्या है? ',
         'ref': '20218ad0-96c8-4799-bdfe-90c689c5c206',
         'properties': {'choices': [{'label': 'पुरुष'},
                                    {'label': 'महिला'},
                                    {'label': 'अन्य'}]},
         'type': 'multiple_choice'}

    qt = {'title': 'What is your gender? ',
          'ref': '20218ad0-96c8-4799-bdfe-90c689c5c206',
          'properties': {
              'choices': [{'label': 'Male'},
                          {'label': 'Female'},
                          {'label': 'Other'}]},
          'type': 'multiple_choice'}

    t = response_translator(q, qt)
    assert t('महिला') == 'Female'

def test_response_translator_works_when_no_other():
    q = {'title': 'Which state do you currently live in?\n- A. foo 91  bar\n- B. Jharkhand\n- C. Odisha\n- D. Uttar Pradesh',
         'ref': '20218ad0-96c8-4799-bdfe-90c689c5c206',
         'properties': {
             'choices': [{'label': 'A'},
                         {'label': 'B'},
                         {'label': 'C'},
                         {'label': 'D'}]},
         'type': 'multiple_choice'}

    t = response_translator(q)
    assert t('B') == 'Jharkhand'


def test_response_translator_works_when_other_and_label():
    hin = {'id': 'mdUpJMSY8Lct',
           'title': 'वर्तमान में आप किस राज्य में रहते हैं?\n- A. छत्तीसगढ़\n- B. झारखंड\n- C. ओडिशा\n- D. उत्तर प्रदेश',
           'ref': 'e959559b-092a-434f-b67f-dca329fab50a',
           'properties': {'choices': [{'label': 'A'},
                                      {'label': 'B'},
                                      {'label': 'C'},
                                      {'label': 'D'}]},
           'type': 'multiple_choice'}

    eng = {'title': 'Which state do you currently live in?\n- A. foo 91  bar\n- B. Jharkhand\n- C. Odisha\n- D. Uttar Pradesh',
           'ref': '20218ad0-96c8-4799-bdfe-90c689c5c206',
           'properties': {'choices': [{'label': 'A'},
                                      {'label': 'B'},
                                      {'label': 'C'},
                                      {'label': 'D'}]},
           'type': 'multiple_choice'}


    t = response_translator(hin, eng)
    assert t('B') == 'Jharkhand'

    t = response_translator(eng, hin)
    assert t('B') == 'झारखंड'



def test_response_translator_works_with_numbers():
    hin = {'id': 'mdUpJMSY8Lct',
           'title': 'वर्तमान में आप किस राज्य में रहते हैं?',
           'ref': 'e959559b-092a-434f-b67f-dca329fab50a',
           'properties': {},
           'type': 'number'}

    eng = {'title': 'How old are you?',
           'ref': '20218ad0-96c8-4799-bdfe-90c689c5c206',
           'properties': {},
           'type': 'number'}


    t = response_translator(hin, eng)
    assert t(12) == 12

    t = response_translator(eng, hin)
    assert t(12) == 12
