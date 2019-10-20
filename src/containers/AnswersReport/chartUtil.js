import {bin} from 'd3-array';

export const computeHistogramData = (resultSet, interval, key) => {
  const d = resultSet.rawData().map(r => r[key])
  const max = d.reduce((a,b) => Math.max(a,b))
  const min = d.reduce((a,b) => Math.min(a,b))

  const b = bin().thresholds(Math.ceil((max - min)/interval))

  return b(d).map(r => ({ interval: `${r.x0} - ${r.x1}`, Users: r.length}))
}
