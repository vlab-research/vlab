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
