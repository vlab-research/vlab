export const getSelectedConf = (conf: any, localFormData: any) => {
  const formDataKeys = Object.keys(localFormData);

  const getFieldKeys = (conf: any) => {
    return conf.fields.map((f: any) => f.name);
  };

  const checker = (arr: any[], target: any[]) =>
    target.every(v => arr.includes(v));

  const index = conf.selector.options.findIndex((option: any) =>
    checker(formDataKeys, getFieldKeys(option))
  );

  return conf.selector.options[index];
};
