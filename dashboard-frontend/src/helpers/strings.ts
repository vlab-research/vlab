export const createSlugFor = (str: string) =>
  str.replace(/\s+/g, '-').toLowerCase();

export const classNames = (...classes: string[]) =>
  classes.filter(Boolean).join(' ');
