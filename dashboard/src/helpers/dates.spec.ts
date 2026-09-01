
import { formatRelativeTime, formatTimestamp } from './dates';

describe('formatTimestamp', () => {
  afterEach(() => jest.useRealTimers());

  // Regression: "Yesterday" used to be guarded by a same-month check, so it was
  // wrong on the 1st of every month — on 2026-09-01 it rendered the day before
  // as "August 31, 2026". These pin the clock rather than reading it, because
  // the old bug was invisible on 28 days out of 30 and turned CI red on the 1st.
  const dayBefore = (today: string) => {
    jest.useFakeTimers().setSystemTime(new Date(today));
    return formatTimestamp(Date.now() - 24 * 60 * 60 * 1000);
  };

  it('says Yesterday across a month boundary', () => {
    expect(dayBefore('2026-09-01T12:00:00Z')).toBe('Yesterday');
  });

  it('says Yesterday across a year boundary', () => {
    expect(dayBefore('2027-01-01T12:00:00Z')).toBe('Yesterday');
  });

  it('says Yesterday mid-month, as it always did', () => {
    expect(dayBefore('2026-09-15T12:00:00Z')).toBe('Yesterday');
  });

  it('can format a milliseconds timestamp into a human readable date', () => {
    const dayInMilliseconds = 24 * 60 * 60 * 1000;
    const currentTimestamp = Date.now();

    expect(formatTimestamp(currentTimestamp)).toBe('Today');
    expect(formatTimestamp(currentTimestamp - dayInMilliseconds)).toBe(
      'Yesterday'
    );
    expect(
      formatTimestamp(new Date('Tue, 09 Mar 2021 12:39:09 GMT').getTime())
    ).toBe('March 09, 2021');
    expect(
      formatTimestamp(new Date('Tue, 09 Mar 9000 12:39:09 GMT').getTime())
    ).toBe('March 09, 9000');
  });
});

describe('formatRelativeTime', () => {
  const ago = (ms: number) => new Date(Date.now() - ms).toISOString();

  it('formats recent timestamps as relative ages', () => {
    expect(formatRelativeTime(ago(10 * 1000))).toBe('just now');
    expect(formatRelativeTime(ago(60 * 1000))).toBe('1 minute ago');
    expect(formatRelativeTime(ago(5 * 60 * 1000))).toBe('5 minutes ago');
    expect(formatRelativeTime(ago(60 * 60 * 1000))).toBe('1 hour ago');
    expect(formatRelativeTime(ago(3 * 60 * 60 * 1000))).toBe('3 hours ago');
    expect(formatRelativeTime(ago(24 * 60 * 60 * 1000))).toBe('1 day ago');
    expect(formatRelativeTime(ago(4 * 24 * 60 * 60 * 1000))).toBe('4 days ago');
  });

  it('falls back to the calendar date beyond 30 days', () => {
    const old = new Date('Tue, 09 Mar 2021 12:39:09 GMT').toISOString();
    expect(formatRelativeTime(old)).toBe('March 09, 2021');
  });

  it('passes through unparseable input unchanged', () => {
    expect(formatRelativeTime('not-a-date')).toBe('not-a-date');
  });
});
