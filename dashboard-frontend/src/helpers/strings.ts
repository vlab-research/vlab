export const createSlugFor = (str: string) =>
  str.replace(/\s+/g, '-').toLowerCase();
