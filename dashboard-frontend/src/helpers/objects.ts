export const mapValueToKey = (value: string, key: string, config: any) => {
  return { value, key, config };
};

export const getInitialValue = (obj: any, key: string) => {
  if (obj[key] === 'text' || obj[key] === 'select') {
    return '';
  }
  if (obj[key] === 'number') {
    return 0;
  }
  return;
};

export const assignObject = (str: string, value: any) => {
  const object = {
    [str]: value,
  };

  return object;
};

export const getValueByProp = (obj: any, key: string) => {
  return obj[key];
};

export const stringLookup = (str: string, arr: any[], key: string) => {
  const index = arr.findIndex(obj => obj[key] === str);
  return arr[index];
};
