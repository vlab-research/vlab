import getNextConf from './getNextConf';

describe('getNextConf', () => {
  const confs = ['conf1', 'conf2', 'conf3'];

  it('when given a conf it returns the next conf in the ordered array of confs', () => {
    const conf = 'conf1';

    const res = getNextConf(confs, conf);
    const expectation = 'conf2';
    expect(res).toEqual(expectation);
  });

  it('exits the function when passed the last conf', () => {
    const conf = 'conf3';

    const res = getNextConf(confs, conf);
    const expectation = undefined;
    expect(res).toEqual(expectation);
  });
});
