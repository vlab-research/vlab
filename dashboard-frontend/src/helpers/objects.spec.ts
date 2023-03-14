import { reducer } from './objects';

describe('reducer', () => {
  it('takes an array of objects and reduces to one single object', () => {
    var arr = [
      { name: 'foo', value: 'bar' },
      { name: 'foobar', value: 'baz' },
    ];

    const expectation = { foo: 'bar', foobar: 'baz' };

    const res = reducer(arr);

    expect(res).toStrictEqual(expectation);
  });
});
