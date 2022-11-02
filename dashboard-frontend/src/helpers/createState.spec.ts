import {
  createInitialState,
  createStateFromArrayOfTuples,
  createStateFromTuple,
} from './createState';

import { general } from './../pages/NewStudyPage/configs/general';
import { creative } from './../pages/NewStudyPage/configs/creative';
import { recruitment_simple } from './../pages/NewStudyPage/configs/recruitment_simple';
import { destination } from './../pages/NewStudyPage/configs/destination';
import { targeting } from './../pages/NewStudyPage/configs/targeting';

describe('createInitialState', () => {
  it('takes a single object and returns an initial state obj', () => {
    const obj = general;
    const key = 'general';

    const expectation = {
      general: {
        name: '',
        objective: '',
        optimization_goal: '',
        destination_type: '',
        page_id: 0,
        min_budget: 0,
        opt_window: 0,
        instagram_id: 0,
        ad_account: 0,
        country: '',
      },
    };

    const res = createInitialState(key, obj);
    expect(res).toStrictEqual(expectation);
  });
});

describe('createStateFromTuple', () => {
  it('takes a tuple made up of key and object and returns an initial state obj', () => {
    const obj = general;
    const key = 'general';
    const tuple = [key, obj];

    const expectation = {
      general: {
        name: '',
        objective: '',
        optimization_goal: '',
        destination_type: '',
        page_id: 0,
        min_budget: 0,
        opt_window: 0,
        instagram_id: 0,
        ad_account: 0,
        country: '',
      },
    };

    const res = createStateFromTuple(tuple);
    expect(res).toStrictEqual(expectation);
  });
});

describe('createStateFromArrayOfTuples', () => {
  it('takes an array of tuples made up of key and object and returns an initial megastate', () => {
    const set = {
      general,
      creative,
    };

    const arrayOfTuples = Object.entries(set);

    const expectation = {
      general: {
        name: '',
        objective: '',
        optimization_goal: '',
        destination_type: '',
        page_id: 0,
        min_budget: 0,
        opt_window: 0,
        instagram_id: 0,
        ad_account: 0,
        country: '',
      },
      creative: {
        destination: '',
        name: '',
        image_hash: '',
        body: '',
        link_text: '',
        welcome_message: '',
        button_text: '',
      },
    };

    const res = createStateFromArrayOfTuples(arrayOfTuples);
    expect(res).toStrictEqual(expectation);

    const set2 = {
      destination,
      targeting,
      recruitment_simple,
    };

    const arrayOfTuples2 = Object.entries(set2);

    const expectation2 = {
      destination: { name: '', initial_shortcode: '', destination: '' },
      targeting: { template_campaign_name: '', distribution_vars: '' }, // TODO – make fn map state to recruitment then recruitment_simple
      recruitment_simple: {
        ad_campaign_name: '',
        budget: 0,
        max_sample: 0,
        start_date: '',
        end_date: '',
      },
    };

    const res2 = createStateFromArrayOfTuples(arrayOfTuples2);
    expect(res2).toStrictEqual(expectation2);
  });
});
