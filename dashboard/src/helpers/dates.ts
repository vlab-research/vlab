export const formatTimestamp = (timestamp: number) => {
  const providedDate = new Date(timestamp);
  const currentDate = new Date();

  if (
    providedDate.getUTCFullYear() === currentDate.getUTCFullYear() &&
    providedDate.getUTCMonth() === currentDate.getUTCMonth()
  ) {
    if (providedDate.getUTCDate() === currentDate.getUTCDate()) {
      return 'Today';
    }

    if (providedDate.getUTCDate() === currentDate.getUTCDate() - 1) {
      return 'Yesterday';
    }
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
