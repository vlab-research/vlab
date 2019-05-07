import moment from 'moment';

export function computeHistogramData(resultSet, interval) {
  const FORMAT = 'HH:mm';
  const timeline = {};
  const dayStart = moment('00:00', FORMAT);
  const current = moment(dayStart);

  const data = resultSet.rawData();
  if (!data.length) return data;

  do {
    timeline[current.format(FORMAT)] = 0;
    current.add(interval, 'm');
  } while (dayStart.format(FORMAT) !== current.format(FORMAT));

  const timelineArray = Object.keys(timeline);

  data.forEach(response => {
    const time = moment(response['Responses.startTime'].slice(11), FORMAT);
    timelineArray.forEach((step, i) => {
      const start = moment(step, FORMAT);
      const end = moment(timelineArray[i + 1], FORMAT);
      if (time.isBetween(start, end, null, '[)')) timeline[step]++;
    });
  });

  const result = timelineArray.reduce((acc, time, idx) => {
    acc.push({
      time: `${time} - ${timelineArray[idx + 1] || timelineArray[0]}`,
      Users: timeline[time],
    });
    return acc;
  }, []);

  return result;
}
