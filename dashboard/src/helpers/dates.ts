const MS_PER_DAY = 24 * 60 * 60 * 1000;

// The UTC calendar day a moment falls on, counted from the epoch.
//
// Counting absolute days is what makes the comparison below safe across month
// and year boundaries. The previous version asked whether two dates shared a
// year and a month before comparing `getUTCDate()`, which meant "yesterday"
// could never be recognised on the 1st: on 2026-09-01 the day before is in
// August, the month guard fails, and the dashboard rendered "August 31, 2026"
// where it should have said "Yesterday". Same bug on Jan 1 across the year.
const utcCalendarDay = (date: Date) =>
  Math.floor(
    Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()) /
      MS_PER_DAY
  );

export const formatTimestamp = (timestamp: number) => {
  const providedDate = new Date(timestamp);
  const currentDate = new Date();

  const daysAgo = utcCalendarDay(currentDate) - utcCalendarDay(providedDate);

  if (daysAgo === 0) {
    return 'Today';
  }

  if (daysAgo === 1) {
    return 'Yesterday';
  }

  return providedDate.toLocaleDateString('en', {
    month: 'long',
    year: 'numeric',
    day: '2-digit',
  });
};

// Renders an ISO timestamp as a short relative age ("5 minutes ago"), falling
// back to the calendar date beyond 30 days. Used by the study errors surface
// ("broken since X", "last seen X").
export const formatRelativeTime = (iso: string): string => {
  const then = new Date(iso).getTime();

  if (isNaN(then)) {
    return iso;
  }

  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 60) {
    return 'just now';
  }

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
  }

  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  }

  const days = Math.floor(hours / 24);
  if (days < 30) {
    return `${days} day${days === 1 ? '' : 's'} ago`;
  }

  return formatTimestamp(then);
};
