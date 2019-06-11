import moment from 'moment';

export const computeHistogramData = (resultSet, interval) => {
  const freqData = {};
  resultSet.rawData().forEach(response => {
    const start = moment(response['Responses.startTime']);
    const end = moment(response['Responses.endTime']);
    const duration = moment.duration(end.diff(start)).asMinutes();
    let max = Math.ceil(duration / interval) * interval;
    if (!max) max = interval;
    freqData[max] = freqData[max] ? freqData[max] + 1 : 1;
  });

  const maxDuration = Math.max(...Object.keys(freqData));
  const stackedData = [];
  for (let i = 0; i < maxDuration; i += interval) {
    let freq = freqData[i + interval];
    if (!freq) freq = 0;
    stackedData.push({ interval: `${i} - ${i + interval}`, Users: freq });
  }
  return stackedData;
};
