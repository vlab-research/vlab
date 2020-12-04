from .marketing import ad_diff, Instruction, StratumConf, make_ref


def test_ad_diff_creates_and_pauses():
    adset = {'id': 'ad'}
    running_ads = [{'id': 'foo', 'status': 'ACTIVE', 'creative': {'id': 'bar'}}]
    current_creatives = [{'name': 'hindi', 'id': 'bar', 'actor_id': '111', 'url_tags': '111'}]
    creatives = [{'name': 'newhindi', 'actor_id': '111', 'url_tags': '123'}]

    instructions = ad_diff(adset, running_ads, current_creatives, creatives)

    assert instructions == [Instruction('ad', 'update', {'status': 'PAUSED'}, 'foo'),
                            Instruction('ad',
                                        'create',
                                        {'adset_id': 'ad',
                                         'name': 'newhindi',
                                         'creative': creatives[0],
                                         'status': 'ACTIVE'},
                                        None)]


def test_ad_diff_leaves_alone_if_already_running():
    # TODO: get status in adset, then you can leave alone and save on api calls
    adset = {'id': 'ad'}
    running_ads = [{'id': 'foo', 'status': 'ACTIVE', 'creative': {'id': 'bar'}}]
    current_creatives = [{'name': 'hindi', 'id': 'bar', 'actor_id': '111', 'url_tags': '111'}]
    creatives = [{'name': 'hindi', 'actor_id': '111', 'url_tags': '111'}]

    instructions = ad_diff(adset, running_ads, current_creatives, creatives)

    assert instructions == []


def test_ad_diff_activates_if_currently_paused():
    # TODO: get status in adset, then you can leave alone and save on api calls
    adset = {'id': 'ad'}
    running_ads = [{'id': 'foo', 'status': 'PAUSED', 'creative': {'id': 'bar'}}]
    current_creatives = [{'name': 'hindi', 'id': 'bar', 'actor_id': '111', 'url_tags': '111'}]
    creatives = [{'name': 'hindi', 'actor_id': '111', 'url_tags': '111'}]

    instructions = ad_diff(adset, running_ads, current_creatives, creatives)

    assert instructions == [Instruction('ad', 'update', {'status': 'ACTIVE'}, 'foo')]


def test_ad_diff_handles_many():
    adset = {'id': 'ad'}
    running_ads = [{'id': 'foo', 'status': 'ACTIVE', 'creative': {'id': 'bar'}},
                   {'id': 'baz', 'status': 'ACTIVE', 'creative': {'id': 'qux'}}]

    current_creatives = [{'name': 'hindi', 'id': 'bar', 'actor_id': '111', 'url_tags': '111'},
                         {'name': 'odia', 'id': 'qux', 'actor_id': '111', 'url_tags': '123'}]

    creatives = [{'name': 'odia', 'actor_id': '111', 'url_tags': '123'},
                 {'name': 'newfoo', 'actor_id': '111', 'url_tags': '124'}]

    instructions = ad_diff(adset, running_ads, current_creatives, creatives)

    assert instructions == [Instruction('ad', 'update', {'status': 'PAUSED'}, 'foo'),
                            Instruction('ad',
                                        'create',
                                        {'adset_id': 'ad',
                                         'name': 'newfoo',
                                         'creative': creatives[1],
                                         'status': 'ACTIVE'},
                                        None)]


def test_ad_diff_leaves_many_alone_if_nothing_to_be_done():
    adset = {'id': 'ad'}
    running_ads = [{'id': 'foo', 'status': 'ACTIVE', 'creative': {'id': 'bar'}},
                   {'id': 'baz', 'status': 'PAUSED', 'creative': {'id': 'qux'}}]

    current_creatives = [{'name': 'hindi', 'id': 'bar', 'actor_id': '111', 'url_tags': '111'},
                         {'name': 'odia', 'id': 'qux', 'actor_id': '111', 'url_tags': '123'}]

    creatives = [{'name': 'hindi', 'actor_id': '111', 'url_tags': '111'}]

    instructions = ad_diff(adset, running_ads, current_creatives, creatives)

    assert instructions == []

def test_make_ref():
    stratum = StratumConf('foo', {'bar': 'baz'}, 10, 'foo', False, {}, [], [])
    ref = make_ref('form1', stratum)
    assert ref == 'form.form1.stratumid.foo.bar.baz'

    stratum = StratumConf('foo', {}, 10, 'foo', False, {}, [], [])
    ref = make_ref('form1', stratum)
    assert ref == 'form.form1.stratumid.foo'


# test
# create new campaign if none (or no??)
#
