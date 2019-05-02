import moment from 'moment';

export const getData = resultSet => {
  const range = 60;
  const freqData = {};
  resultSet
    .rawData()
    .filter(response => response['Responses.formid'] === 'form1')
    .forEach(response => {
      const start = moment(response['Responses.startTime']);
      const end = moment(response['Responses.endTime']);
      const duration = moment.duration(end.diff(start)).asMinutes();
      let max = Math.ceil(duration / range) * range;
      if (!max) max = range;
      freqData[max] = freqData[max] ? freqData[max] + 1 : 1;
    });

  const maxDuration = Math.max(...Object.keys(freqData));
  const stackedData = [];
  for (let i = 0; i < maxDuration; i += range) {
    let freq = freqData[i + range];
    if (!freq) freq = 0;
    stackedData.push({ interval: `${i} - ${i + range}`, freq });
  }
  return stackedData;
};
