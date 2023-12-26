import { createStrataFromVariables, getFinishQuestionRef } from './strata';
import { Stratum } from '../../../../types/conf';
import { Variables, Creatives } from '../types/conf';

describe('createStrataFromVariables', () => {
  it('Empty variables create empty strata', () => {

    const variables: Variables = [];
    const creatives = undefined;
    const strata = createStrataFromVariables(variables, creatives);

    expect(strata).toEqual([])
  });

  it('Works with one variable and multiple levels', () => {

    const variables: Variables = [
      {
        name: 'gender',
        properties: ['genders'],
        levels: [
          { name: 'men', template_campaign: 'foo', template_adset: 'men', facebook_targeting: { 'genders': [1] }, quota: 0.5 },
          { name: 'women', template_campaign: 'foo', template_adset: 'women', facebook_targeting: { 'genders': [2] }, quota: 0.5 }
        ]
      }
    ];

    const creatives: Creatives = [];
    const strata = createStrataFromVariables(variables, "foo", creatives);

    expect(strata).toEqual([
      {
        audiences: [],
        excluded_audiences: [],
        metadata: { gender: "men" },
        creatives: [],
        facebook_targeting: { genders: [1] },
        question_targeting: {
          op: "and",
          vars: [
            {
              op: "equal",
              vars: [
                {
                  type: "variable",
                  value: "gender"
                },
                {
                  type: "constant",
                  value: "men"
                }
              ]
            },
            {
              op: "answered",
              vars: [
                {
                  type: "variable",
                  value: "foo"
                }
              ]
            }
          ]
        },
        quota: 0.5,
        id: 'gender:men'
      },
      {
        audiences: [],
        excluded_audiences: [],
        metadata: { gender: "women" },
        creatives: [],
        facebook_targeting: { genders: [2] },
        question_targeting: {
          op: "and",
          vars: [
            {
              op: "equal",
              vars: [
                {
                  type: "variable",
                  value: "gender"
                },
                {
                  type: "constant",
                  value: "women"
                }
              ]
            },
            {
              op: "answered",
              vars: [
                {
                  type: "variable",
                  value: "foo"
                }
              ]
            }
          ]
        },
        quota: 0.5,
        id: 'gender:women'
      }
    ])
  });

  it('Creates product of two variables and multiple levels', () => {

    const variables: Variables = [
      {
        name: 'gender',
        properties: ['genders'],
        levels: [
          { name: 'men', template_campaign: 'foo', template_adset: 'men', facebook_targeting: { 'genders': [1] }, quota: 0.5 },
          { name: 'women', template_campaign: 'foo', template_adset: 'women', facebook_targeting: { 'genders': [2] }, quota: 0.5 }
        ]
      },
      {
        name: 'age',
        properties: ['age_min', 'age_max'],
        levels: [
          { name: '18', template_campaign: 'foo', template_adset: '18-34', facebook_targeting: { 'age_min': 18, 'age_max': 34 }, quota: 0.5 },
          { name: '35', template_campaign: 'foo', template_adset: '35-65', facebook_targeting: { 'age_min': 35, 'age_max': 65 }, quota: 0.5 }
        ]
      }
    ];

    const creatives = undefined;
    const strata = createStrataFromVariables(variables, "foo", creatives);

    expect(strata).toEqual([
      {
        audiences: [],
        excluded_audiences: [],
        metadata: { gender: "men", age: "18" },
        creatives: [],
        facebook_targeting: { genders: [1], age_min: 18, age_max: 34 },
        question_targeting: {
          op: "and",
          vars: [
            {
              op: "equal",
              vars: [
                {
                  type: "variable",
                  value: "gender"
                },
                {
                  type: "constant",
                  value: "men"
                }
              ]
            },
            {
              op: "equal",
              vars: [
                {
                  type: "variable",
                  value: "age"
                },
                {
                  type: "constant",
                  value: "18"
                }
              ]
            },
            {
              op: "answered",
              vars: [
                {
                  type: "variable",
                  value: "foo"
                }
              ]
            }
          ]
        },
        quota: 0.25,
        id: 'gender:men,age:18'
      },
      {
        audiences: [],
        excluded_audiences: [],
        metadata: { gender: "men", age: "35" },
        creatives: [],
        facebook_targeting: { genders: [1], age_min: 35, age_max: 65 },
        question_targeting: {
          op: "and",
          vars: [
            {
              op: "equal",
              vars: [
                {
                  type: "variable",
                  value: "gender"
                },
                {
                  type: "constant",
                  value: "men"
                }
              ]
            },
            {
              op: "equal",
              vars: [
                {
                  type: "variable",
                  value: "age"
                },
                {
                  type: "constant",
                  value: "35"
                }
              ]
            },
            {
              op: "answered",
              vars: [
                {
                  type: "variable",
                  value: "foo"
                }
              ]
            }
          ]
        },
        quota: 0.25,
        id: 'gender:men,age:35'
      },
      {
        audiences: [],
        excluded_audiences: [],
        metadata: { gender: "women", age: "18" },
        creatives: [],
        facebook_targeting: { genders: [2], age_min: 18, age_max: 34 },
        question_targeting: {
          op: "and",
          vars: [
            {
              op: "equal",
              vars: [
                {
                  type: "variable",
                  value: "gender"
                },
                {
                  type: "constant",
                  value: "women"
                }
              ]
            },
            {
              op: "equal",
              vars: [
                {
                  type: "variable",
                  value: "age"
                },
                {
                  type: "constant",
                  value: "18"
                }
              ]
            },
            {
              op: "answered",
              vars: [
                {
                  type: "variable",
                  value: "foo"
                }
              ]
            }
          ]
        },
        quota: 0.25,
        id: 'gender:women,age:18'
      },
      {
        audiences: [],
        excluded_audiences: [],
        metadata: { gender: "women", age: "35" },
        creatives: [],
        facebook_targeting: { genders: [2], age_min: 35, age_max: 65 },
        question_targeting: {
          op: "and",
          vars: [
            {
              op: "equal",
              vars: [
                {
                  type: "variable",
                  value: "gender"
                },
                {
                  type: "constant",
                  value: "women"
                }
              ]
            },
            {
              op: "equal",
              vars: [
                {
                  type: "variable",
                  value: "age"
                },
                {
                  type: "constant",
                  value: "35"
                }
              ]
            },
            {
              op: "answered",
              vars: [
                {
                  type: "variable",
                  value: "foo"
                }
              ]
            }
          ]
        },
        quota: 0.25,
        id: 'gender:women,age:35'
      },
    ])
  });


  it('Creates product of three variables and multiple levels', () => {

    const variables: Variables = [
      {
        name: 'gender',
        properties: ['genders'],
        levels: [
          { name: 'men', template_campaign: 'foo', template_adset: 'men', facebook_targeting: { 'genders': [1] }, quota: 0.5 },
          { name: 'women', template_campaign: 'foo', template_adset: 'women', facebook_targeting: { 'genders': [2] }, quota: 0.5 }
        ]
      },
      {
        name: 'age',
        properties: ['age_min', 'age_max'],
        levels: [
          { name: '18', template_campaign: 'foo', template_adset: '18-34', facebook_targeting: { 'age_min': 18, 'age_max': 34 }, quota: 0.5 },
          { name: '35', template_campaign: 'foo', template_adset: '35-65', facebook_targeting: { 'age_min': 35, 'age_max': 65 }, quota: 0.5 }
        ]
      },
      {
        name: 'location',
        properties: ['geo_location'],
        levels: [
          { name: 'foo', template_campaign: 'foo', template_adset: 'foo', facebook_targeting: { 'geo_location': { city: 'foo' } }, quota: 0.5 },
          { name: 'bar', template_campaign: 'foo', template_adset: 'bar', facebook_targeting: { geo_location: { city: 'bar' } }, quota: 0.5 },
          { name: 'baz', template_campaign: 'foo', template_adset: 'baz', facebook_targeting: { geo_location: { city: 'baz' } }, quota: 0.5 }
        ]
      }
    ];


    const creatives = undefined;
    const strata = createStrataFromVariables(variables, "foo", creatives);

    expect(strata.length).toBe(12)
    expect(strata.filter(s => s.facebook_targeting.age_min === 35).length).toBe(6)
    expect(strata.filter(s => s.facebook_targeting.age_min === 18).length).toBe(6)
    expect(strata.filter(s => s.facebook_targeting.genders[0] === 1).length).toBe(6)
    expect(strata.filter(s => s.facebook_targeting.genders[0] === 2).length).toBe(6)
    expect(strata.filter(s => s.facebook_targeting.geo_location.city === 'foo').length).toBe(4)
    expect(strata.filter(s => s.facebook_targeting.geo_location.city === 'bar').length).toBe(4)
    expect(strata.filter(s => s.facebook_targeting.geo_location.city === 'baz').length).toBe(4)
  });


});

describe("getFinishQuestionRef", () => {

  it("gets null value in a basic case", () => {
    const strata: Stratum[] = []
    const res = getFinishQuestionRef(strata)
    expect(res).toEqual('')

  })

  it("gets the ref in a basic case", () => {
    const strata = [
      {
        audiences: [],
        excluded_audiences: [],
        metadata: { gender: "men" },
        creatives: [],
        facebook_targeting: { genders: [1] },
        question_targeting: {
          op: "and",
          vars: [
            {
              op: "equal",
              vars: [
                {
                  type: "variable",
                  value: "gender"
                },
                {
                  type: "constant",
                  value: "men"
                }
              ]
            },
            {
              op: "answered",
              vars: [
                {
                  type: "variable",
                  value: "foo"
                }
              ]
            }
          ]
        },
        quota: 0.5,
        id: 'gender:men'
      }]

    const res = getFinishQuestionRef(strata)
    expect(res).toEqual("foo")
  })


})
