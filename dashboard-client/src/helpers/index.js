import Validator from './argValidation';

function groupBy(arr, fn) {
  const m = new Map();
  arr.forEach((el) => {
    const k = fn(el);
    m.set(k, m.has(k) ? [...m.get(k), el] : [el]);
  });
  return m;
}


export { Validator, groupBy };
