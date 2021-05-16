import moment from 'moment';

export function computeHistogramData(resultSet, interval) {
  const FORMAT = 'HH:mm';
  const timeline = {};
  const dayStart = moment('00:00', FORMAT);
  const dayStartFormat = dayStart.format(FORMAT);
  const current = moment(dayStart);

  const data = resultSet.rawData();
  if (!data.length) return data;

  do {
    timeline[current.format(FORMAT)] = 0;
    current.add(interval, 'm');
  } while (dayStartFormat !== current.format(FORMAT));

  const timeArr = Object.keys(timeline);
  const timeArrFormat = timeArr.map(step => moment(step, FORMAT));

  data.forEach((response) => {
    const time = moment(response['Responses.startTime'].slice(11), FORMAT);
    timeArrFormat.forEach((step, i) => {
      if (time.isBetween(step, timeArrFormat[i + 1], null, '[)')) {
        timeline[timeArr[i]]++;
      }
    });
  });

  return timeArr.reduce((acc, time, idx) => {
    acc.push({
      time: `${time} - ${timeArr[idx + 1] || timeArr[0]}`,
      Users: timeline[time],
    });
    return acc;
  }, []);
}
