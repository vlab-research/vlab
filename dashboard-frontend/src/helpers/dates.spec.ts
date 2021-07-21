import { formatTimestamp } from './dates';

describe('formatTimestamp', () => {
  it('can format a milliseconds timestamp into a human readable date', () => {
    const dayInMilliseconds = 24 * 60 * 60 * 1000;
    const currentTimestamp = Date.now();

    expect(formatTimestamp(currentTimestamp)).toBe('Today');
    expect(formatTimestamp(currentTimestamp - dayInMilliseconds)).toBe(
      'Yesterday'
    );
    expect(
      formatTimestamp(new Date('Tue, 09 Mar 2021 01:39:09 GMT').getTime())
    ).toBe('March 09, 2021');
    expect(
      formatTimestamp(new Date('Tue, 09 Mar 9000 01:39:09 GMT').getTime())
    ).toBe('March 09, 9000');
  });
});
