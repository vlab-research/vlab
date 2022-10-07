export const createSlugFor = (str: string) =>
  str.replace(/\s+/g, '-').toLowerCase();

export const classNames = (...classes: string[]) =>
  classes.filter(Boolean).join(' ');

export const toCamelCase = (str: string) => {
  const regExp = /[-_]\w/gi;
  return str.replace(regExp, match => {
    return match[1].toUpperCase();
  });
};
