import moment from 'moment';

export const computeHistogramData = resultSet => {
  const dates = resultSet.rawData().map(response => moment(response['Responses.startTime']));
  const maxDate = moment.max(dates);
  const minDate = moment.min(dates);
  const intervalDates = [];
  let keyDate = minDate.clone();
  while (keyDate.isSameOrBefore(maxDate)) {
    intervalDates.push({
      timestamp: keyDate.toString(),
      date: keyDate.format('ll'),
      users: 0,
    });
    keyDate = keyDate.add(1, 'days');
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
