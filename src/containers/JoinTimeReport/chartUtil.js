import moment from 'moment';

export const computeHistogramData = (resultSet, interval) => {
  const dates = resultSet.rawData().map(response => moment(response['Responses.startTime']));
  if (!dates.length) return [];
  const maxDate = moment.max(dates);
  const minDate = moment.min(dates);
  const intervalDates = [];
  let keyDate = minDate.clone();
  const intervalKey = interval ? 'months' : 'days';
  const formatKey = interval ? 'MMM, YYYY' : 'D, MMM, YYYY';
  while (keyDate.isSameOrBefore(maxDate)) {
    intervalDates.push({
      timestamp: keyDate.format(),
      date: keyDate.format(formatKey),
      users: 0,
    });
    keyDate = keyDate.add(1, intervalKey);
  }
  dates.forEach(date => {
    for (let i = 0; i < intervalDates.length; i++) {
      const topDate = intervalDates[i].timestamp;
      if (date.isSameOrBefore(topDate)) {
        intervalDates[i].users++;
        break;
      }
    }
  });
  return intervalDates;
};
