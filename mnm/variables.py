questions = [
    ("fever2weeks", "ab9e9369-458f-4de6-af85-df62bc57cb82"),
    ("longsleeves", "3571207f-3fe9-4fd2-8714-9514e91a2a45"),
    ("seekhelpfever", "99ca4be9-3348-4a81-a3be-02e6dbe7a318"),
    ("timeseekhelpfever", "41f68347-e0bd-4b4d-84d4-8da5e898660b"),
    ("malaria2weeks", "58583e72-7036-4c74-9ebd-179598cba59f"),
    ("testmalaria", "8f8921dd-2299-4de3-ab21-0796865f9801"),
    ("timeseekhelpmalaria", "ac38821e-7c2e-443c-8cfa-1cddd0320f2d"),
    ("sleepundernet", "1f812d37-a7a5-400d-8a31-145fbb49f577"),
    ("membersbednet", "57badd12-1206-4f36-a83c-f77691d985b8"),
]

# TODO: just write the vars in Typeform?

questions += [
    ("gender", "20218ad0-96c8-4799-bdfe-90c689c5c206"),
    ("membersbednet", "8065d101-7995-4471-9ca6-54e9ce6d4310"),
    ("familymembers", "254fe756-eab6-4989-8c80-acb0bb6ec52b"),
    ("pregnantwoman", "0733cbf7-575b-4f5b-8f76-95e5298dff5e"),
    ("distancemedicalcenter", "d7573919-8a7e-457f-9a1d-1f8c389127a7"),
    ("education", "e40fa1c6-13a1-4a02-91cd-0eaade11864d"),
    ("age", "da3d1de1-a287-4143-8b2c-107565a4e4d4"),
    ("religion", "8e490114-df6d-4fb3-b1be-6ce11acd9212"),
    ("caste", "912bc5d8-db4a-402b-b506-f85ce4e89e6f"),
    ("hasmosquitonet", "bd4802c6-7bdb-40f0-aac1-18cc6df7da6e"),
    ("hasairconditioning", "e279587c-975f-433a-adab-1ad563876af6"),
    ("worried_covid", "25b20f99-a30c-4549-968a-05b7276fa485"),
    ("worried_malaria", "7c955b2b-0480-4cbc-9800-f94b77078f22"),
    # ("seekhelpfever", "f526f205-7aa9-4e3a-9acc-c39766e1bc8c"),
    ("malaria5year", "f6e69027-97cc-494e-8d52-318b75047e23"),
    ("malaria2weeks", "dad23031-8468-4900-89cc-d01841d8b660"),
    ("fever2weeks", "8327f607-0ebe-4db5-9708-2b6207cc2483"),
    ("seekhelpfever", "e6d4dc10-85e8-43c8-ad44-295305027958"),
    ("timeseekhelpfever", "96d6dba5-bd1e-4fef-a71a-cc20fbca7ca4"),
    ("timeseekhelpmalaria", "73ef8720-5e2b-463c-aa8a-ed890a839a8b"),
    ("testmalaria", "9de3d2f5-d9c0-45aa-9065-a61c975a58dc"),
    ("sleepundernet", "b5b1ff58-c8df-4890-9b1c-0cd40ce6edc0"),
    ("longsleeves", "0992f107-7274-4404-aeff-bf80a723f098"),
    ("used_spray", "02379921-3b90-4005-b813-cf1e9aec0f40"),
    ("home", "4d0ae478-3893-4b46-ab39-d6848c69245d"),
    ("occupation", "4fc929c7-132d-49b1-a164-515e5cc9064f"),
]

variable_lookup = {v: k for k, v in questions}
assert len(questions) == len(variable_lookup)
