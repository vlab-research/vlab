export const mapValueToKey = (value: string, key: string, config: any) => {
  return { value, key, config };
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
  }
};

export const checkPropertyExists = (obj: any, prop: string) => {
  return Object.keys(obj).some(key => key === prop);
};

export const reducer = (arr: any[]) => {
  return arr.reduce(
    (obj: any, item: any) => ({ ...obj, [item.name]: item.value }),
    {}
  );
};
