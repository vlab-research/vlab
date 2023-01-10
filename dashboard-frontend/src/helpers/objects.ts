export const mapValueToKey = (value: string, key: string, config: any) => {
  return { value, key, config };
};

export const getInitialValue = (obj: any, key: string) => {
  if (obj[key] === 'text') {
    return '';
  }
  if (obj[key] === 'select') {
    return {};
  }
  if (obj[key] === 'number') {
    return 0;
  }
  if (obj[key] === 'list') {
    return [];
  }
  if (obj[key] === 'configSelect') {
    return {};
  }
  if (obj[key] === 'configList') {
    return [];
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

export const isJSON = (strData: any) => {
  if (JSON.parse(strData)) {
    return true;
  } else {
    return false;
  }
};

export const checkPropertyExists = (obj: any, prop: string) => {
  const keys = Object.keys(obj);
  console.log(keys.some(key => key === prop));
  return keys.some(key => key === prop);
};
