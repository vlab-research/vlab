from .marketing import *



def test_ad_diff_creates_and_pauses():
    adset = {'id': 'ad'}
    running_ads = [{'id': 'foo', 'creative': {'id': 'bar'}}]
    current_creatives = [{ 'name': 'hindi', 'id': 'bar', 'actor_id': '111', 'url_tags': '111'}]
    creatives = [{'name': 'newhindi', 'actor_id': '111', 'url_tags': '123'}]

    instructions = ad_diff(adset, running_ads, current_creatives, creatives)

    assert instructions == [Instruction('ad', 'update', {'status': 'PAUSED'}, 'foo'),
                            Instruction('ad',
                                        'create',
                                        {'adset_id': 'ad', 'name': 'newhindi', 'creative': creatives[0], 'status': 'ACTIVE'},
                                        None)]


def test_ad_diff_leaves_alone_with_active_update():
    adset = {'id': 'ad'}
    running_ads = [{'id': 'foo', 'creative': {'id': 'bar'}}]
    current_creatives = [{ 'name': 'hindi', 'id': 'bar', 'actor_id': '111', 'url_tags': '111'}]
    creatives = [{'name': 'hindi', 'actor_id': '111', 'url_tags': '111'}]

    instructions = ad_diff(adset, running_ads, current_creatives, creatives)

    assert instructions == [Instruction('ad', 'update', {'status': 'ACTIVE'}, 'foo')]

def test_ad_diff_handles_many():
    adset = {'id': 'ad'}
    running_ads = [{'id': 'foo', 'creative': {'id': 'bar'}}, {'id': 'baz', 'creative': {'id': 'qux'}}]
    current_creatives = [{'name': 'hindi', 'id': 'bar', 'actor_id': '111', 'url_tags': '111'},
                         {'name': 'odia',  'id': 'qux', 'actor_id': '111', 'url_tags': '123'}]
    creatives = [{'name': 'odia', 'actor_id': '111', 'url_tags': '123'}, {'name': 'newfoo', 'actor_id': '111', 'url_tags': '124'}]

    instructions = ad_diff(adset, running_ads, current_creatives, creatives)

    assert instructions == [Instruction('ad', 'update', {'status': 'PAUSED'}, 'foo'),
                            Instruction('ad', 'update', {'status': 'ACTIVE'}, 'baz'),
                            Instruction('ad',
                                        'create',
                                        {'adset_id': 'ad', 'name': 'newfoo', 'creative': creatives[1], 'status': 'ACTIVE'},
                                        None)]
