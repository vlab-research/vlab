export const createSlugFor = (str: string) => {
  const s = str.replace(/\s+/g, '-').replace(/-+/g, '-').toLowerCase();
  return s
}

export const classNames = (...classes: string[]) =>
  classes.filter(Boolean).join(' ');

export const toCamelCase = (str: string) => {
  const regExp = /[-_]\w/gi;
  return str.replace(regExp, match => {
    return match[1].toUpperCase();
  });
};

export const createLabelFor = (str: string) => {
  let res = toCamelCase(str)
    .replace(/([A-Z])/g, ' $1')
    .trim();
  return res.charAt(0).toUpperCase() + res.slice(1);
};

export const createNameFor = (str: string) => {
  return str.replace(/ /g, '_').toLowerCase();
};
