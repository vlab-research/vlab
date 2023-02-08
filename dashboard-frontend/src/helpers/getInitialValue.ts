export const getInitialValue = (obj: any, key: string) => {
  if (obj[key] === 'text') {
    return '';
  }
  if (obj[key] === 'select') {
    return '';
  }
  if (obj[key] === 'number') {
    return 0;
  }
  if (obj[key] === 'list') {
    return [];
  }
  if (obj[key] === 'configSelect') {
    return '';
  }
  if (obj[key] === 'configList') {
    return [];
  }
  return;
};
