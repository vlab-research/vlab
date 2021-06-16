import moment from 'moment';

export const computeHistogramData = (resultSet, interval, fn) => {
  const freqData = {};
  resultSet.rawData().forEach((response) => {
    const start = moment(response['Responses.startTime']);
    const end = moment(response['Responses.endTime']);
    const duration = moment.duration(end.diff(start))[fn]();
    let max = Math.ceil(duration / interval) * interval;
    if (!max) max = interval;
    freqData[max] = freqData[max] ? freqData[max] + 1 : 1;
  });

  const defaultMax = interval * 8;
  const maxDuration = Math.max(...Object.keys(freqData));
  const mx = maxDuration > defaultMax ? defaultMax : maxDuration;

  const stackedData = [];
  for (let i = 0; i < mx; i += interval) {
    let freq = freqData[i + interval];
    if (!freq) freq = 0;
    stackedData.push({ interval: `${i} - ${i + interval}`, Users: freq });
  }
  return stackedData;
};
