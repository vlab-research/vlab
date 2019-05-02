import moment from 'moment';

export const getData = resultSet => {
  const data = resultSet
    .rawData()
    .filter(response => response['Responses.formid'] === 'form1')
    .map(response => {
      const start = moment(response['Responses.startTime']);
      const end = moment(response['Responses.endTime']);
      return {
        duration: moment.duration(end.diff(start)).asMinutes(),
        userid: response['Responses.userid'],
      };
    });
  const range = 60;
  const freqData = {};
  data.forEach(el => {
    let max = Math.ceil(el.duration / range) * range;
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
