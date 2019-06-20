export const computeHistogramData = (resultSet, interval) => {
  const ansFreq = {};
  const stackedData = [];
  resultSet.rawData().forEach(response => {
    const key = response['Responses.uniqueUserCount'];
    const max = Math.ceil(key / interval) * interval;
    if (ansFreq[max]) ansFreq[max]++;
    else ansFreq[max] = 1;
  });
  const maxInterval = Math.max(...Object.keys(ansFreq));
  for (let i = 0; i < maxInterval; i += interval) {
    let freq = ansFreq[i + interval];
    if (!freq) freq = 0;
    stackedData.push({ interval: `${i} - ${i + interval}`, Users: freq });
  }
  return stackedData;
};
