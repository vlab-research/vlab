import {bin} from 'd3-array';

export const computeHistogramData = (resultSet, interval, key) => {
  const d = resultSet.rawData().map(r => r[key]);
  const max = d.reduce((a,b) => Math.max(a,b), 5);
  const min = d.reduce((a,b) => Math.min(a,b), 0);

  const b = bin().thresholds(Math.ceil((max - min) / interval));

  return b(d).map(r => ({ interval: `${r.x0} - ${r.x1}`, Users: r.length}));
}
