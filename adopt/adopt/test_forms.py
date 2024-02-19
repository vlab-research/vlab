from datetime import datetime

import pytest

from .forms import *


def test_make_answers_labelled():
    q = {
        "title": "What is your gender? ",
        "ref": "20218ad0-96c8-4799-bdfe-90c689c5c206",
        "properties": {
            "choices": [{"label": "Male"}, {"label": "Female"}, {"label": "Other"}]
        },
        "type": "multiple_choice",
    }

    res = make_answers(q)
    assert res == [("Male", "Male"), ("Female", "Female"), ("Other", "Other")]


def test_make_answers_to_notify():
    q = {
        "title": "What is your gender? ",
        "ref": "20218ad0-96c8-4799-bdfe-90c689c5c206",
        "properties": {"description": "type: notify"},
        "type": "statement",
    }

    res = make_answers(q)
    assert res == [("Notify Me", "Notify Me")]


def test_make_answers_labelled_with_dash():
    q = {
        "title": "Which state do you currently live in?\n- A. foo 91  bar\n- B. Jharkhand\n- C. Odisha\n- D. Uttar Pradesh",
        "ref": "20218ad0-96c8-4799-bdfe-90c689c5c206",
        "properties": {
            "choices": [{"label": "A"}, {"label": "B"}, {"label": "C"}, {"label": "D"}]
        },
        "type": "multiple_choice",
    }

    res = make_answers(q)
    assert res == [
        ("A", "foo 91  bar"),
        ("B", "Jharkhand"),
        ("C", "Odisha"),
        ("D", "Uttar Pradesh"),
    ]


def test_make_answers_labelled_without_dash():
    q = {
        "title": "Which state do you currently live in?\nA. foo 91  bar\nB. Jharkhand\nC. Odisha\nD. Uttar Pradesh",
        "ref": "20218ad0-96c8-4799-bdfe-90c689c5c206",
        "properties": {
            "choices": [{"label": "A"}, {"label": "B"}, {"label": "C"}, {"label": "D"}]
        },
        "type": "multiple_choice",
    }

    res = make_answers(q)
    assert res == [
        ("A", "foo 91  bar"),
        ("B", "Jharkhand"),
        ("C", "Odisha"),
        ("D", "Uttar Pradesh"),
    ]


def test_response_translator_translate_when_other():
    q = {
        "id": "vjl6LihKMtcX",
        "title": "आपका लिंग क्या है? ",
        "ref": "20218ad0-96c8-4799-bdfe-90c689c5c206",
        "properties": {
            "choices": [{"label": "पुरुष"}, {"label": "महिला"}, {"label": "अन्य"}]
        },
        "type": "multiple_choice",
    }

    qt = {
        "title": "What is your gender? ",
        "ref": "20218ad0-96c8-4799-bdfe-90c689c5c206",
        "properties": {
            "choices": [{"label": "Male"}, {"label": "Female"}, {"label": "Other"}]
        },
        "type": "multiple_choice",
    }

    t = response_translator(q, qt)
    assert t("महिला") == "Female"


def test_response_translator_works_when_no_other():
    q = {
        "title": "Which state do you currently live in?\n- A. foo 91  bar\n- B. Jharkhand\n- C. Odisha\n- D. Uttar Pradesh",
        "ref": "20218ad0-96c8-4799-bdfe-90c689c5c206",
        "properties": {
            "choices": [{"label": "A"}, {"label": "B"}, {"label": "C"}, {"label": "D"}]
        },
        "type": "multiple_choice",
    }

    t = response_translator(q)
    assert t("B") == "Jharkhand"


def test_response_translator_works_when_other_and_label():
    hin = {
        "id": "mdUpJMSY8Lct",
        "title": "वर्तमान में आप किस राज्य में रहते हैं?\n- A. छत्तीसगढ़\n- B. झारखंड\n- C. ओडिशा\n- D. उत्तर प्रदेश",
        "ref": "e959559b-092a-434f-b67f-dca329fab50a",
        "properties": {
            "choices": [{"label": "A"}, {"label": "B"}, {"label": "C"}, {"label": "D"}]
        },
        "type": "multiple_choice",
    }

    eng = {
        "title": "Which state do you currently live in?\n- A. foo 91  bar\n- B. Jharkhand\n- C. Odisha\n- D. Uttar Pradesh",
        "ref": "20218ad0-96c8-4799-bdfe-90c689c5c206",
        "properties": {
            "choices": [{"label": "A"}, {"label": "B"}, {"label": "C"}, {"label": "D"}]
        },
        "type": "multiple_choice",
    }

    t = response_translator(hin, eng)
    assert t("B") == "Jharkhand"

    t = response_translator(eng, hin)
    assert t("B") == "झारखंड"


def test_response_translator_works_with_numbers():
    hin = {
        "id": "mdUpJMSY8Lct",
        "title": "वर्तमान में आप किस राज्य में रहते हैं?",
        "ref": "e959559b-092a-434f-b67f-dca329fab50a",
        "properties": {},
        "type": "number",
    }

    eng = {
        "title": "How old are you?",
        "ref": "20218ad0-96c8-4799-bdfe-90c689c5c206",
        "properties": {},
        "type": "number",
    }

    t = response_translator(hin, eng)
    assert t(12) == 12

    t = response_translator(eng, hin)
    assert t(12) == 12


def test_response_translator_raises_if_not_matching_types():
    hin = {
        "id": "mdUpJMSY8Lct",
        "title": "वर्तमान में आप किस राज्य में रहते हैं?",
        "ref": "e959559b-092a-434f-b67f-dca329fab50a",
        "properties": {},
        "type": "number",
    }

    eng = {
        "title": "How old are you?",
        "ref": "20218ad0-96c8-4799-bdfe-90c689c5c206",
        "properties": {},
        "type": "short_text",
    }

    with pytest.raises(TranslationError):
        t = response_translator(hin, eng)


def test_translate_response_throws_translation_errors():
    with pytest.raises(TranslationError):
        translate_response({}, "foo", "bar", "baz")

    with pytest.raises(TranslationError):
        translate_response({"foo": {"baz": lambda x: x}}, "foo", "bar", "baz")


def test_translate_response_throws_translates():
    res = translate_response({"foo": {"bar": lambda x: "qux"}}, "foo", "bar", "baz")

    assert res == "qux"


forms = [
    {
        "id": "1",
        "metadata": {"language": "english", "wave": 0},
        "created": datetime(2020, 1, 1),
        "form_json": {
            "fields": [
                {
                    "title": "Which state do you currently live in?\n- A. foo 91  bar\n- B. Jharkhand\n- C. Odisha\n- D. Uttar Pradesh",
                    "ref": "eng0",
                    "properties": {
                        "choices": [
                            {"label": "A"},
                            {"label": "B"},
                            {"label": "C"},
                            {"label": "D"},
                        ]
                    },
                    "type": "multiple_choice",
                }
            ]
        },
    },
    {
        "id": "2",
        "metadata": {"language": "english", "wave": 1},
        "created": datetime(2020, 1, 1),
        "form_json": {
            "fields": [
                {
                    "title": "How old are you?",
                    "ref": "eng1",
                    "properties": {},
                    "type": "number",
                }
            ]
        },
    },
    {
        "id": "3",
        "metadata": {"language": "hindi", "wave": 0},
        "created": datetime(2020, 1, 1),
        "form_json": {
            "fields": [
                {
                    "id": "mdUpJMSY8Lct",
                    "title": "वर्तमान में आप किस राज्य में रहते हैं?\n- A. छत्तीसगढ़\n- B. झारखंड\n- C. ओडिशा\n- D. उत्तर प्रदेश",
                    "ref": "hindi0",
                    "properties": {
                        "choices": [
                            {"label": "A"},
                            {"label": "B"},
                            {"label": "C"},
                            {"label": "D"},
                        ]
                    },
                    "type": "multiple_choice",
                }
            ]
        },
    },
    {
        "id": "4",
        "metadata": {"language": "hindi", "wave": 1},
        "created": datetime(2020, 1, 1),
        "form_json": {
            "fields": [
                {
                    "id": "mdUpJMSY8Lct",
                    "title": "वर्तमान में आप किस राज्य में रहते हैं?",
                    "ref": "hindi1",
                    "properties": {},
                    "type": "number",
                }
            ]
        },
    },
]


def test_translators_for_survey_organize_and_translate():
    t = translators_for_survey(forms, {"reference": "english", "field": "language"})
    assert t["1"]["eng0"]("B") == "Jharkhand"
    assert t["3"]["hindi0"]("B") == "Jharkhand"
    assert t["4"]["hindi1"](100) == 100


def test_translators_for_survey_organize_and_translate_reverse():
    t = translators_for_survey(forms, {"reference": "hindi", "field": "language"})
    assert t["1"]["eng0"]("B") == "झारखंड"
    assert t["3"]["hindi0"]("B") == "झारखंड"
    assert t["4"]["hindi1"](100) == 100


def test_translators_errors_if_no_other_dimensions():
    f = [{**f, "metadata": {"language": f["metadata"]["language"]}} for f in forms]
    with pytest.raises(TranslationError):
        t = translators_for_survey(f, {"reference": "english", "field": "language"})
        assert t["1"]["eng0"]("B") == "झारखंड"
        assert t["3"]["hindi0"]("B") == "झारखंड"
        assert t["4"]["hindi1"](100) == 100


def test_translators_does_not_error_if_no_other_dimensions_but_one_form_per_lang():
    f = [
        {**f, "metadata": {"language": f["metadata"]["language"]}}
        for f in forms
        if f["metadata"]["wave"] == 0
    ]

    t = translators_for_survey(f, {"reference": "english", "field": "language"})
    assert t["1"]["eng0"]("B") == "Jharkhand"
    assert t["3"]["hindi0"]("B") == "Jharkhand"
