import { validate } from './objects';

describe('validate', () => {
  it('takes two objects and checks for a match between keys', () => {
    const obj1 = {
      a: 1,
      b: 2,
      c: 3,
    };
    const obj2 = {
      a: 4,
      b: 5,
      c: 6,
    };

    const res = validate(obj1, obj2);

    expect(res).toBe(true);

    const obj3 = {
      a: 1,
      b: 2,
      c: 3,
    };
    const obj4 = {
      c: 4,
      b: 5,
      a: 6,
    };

    const res2 = validate(obj3, obj4);

    expect(res2).toBe(false);
  });
});
