import { ConfSelectBase, ConfBase, ConfListBase } from '../types/conf';

export const mergeConfs = (conf: ConfSelectBase, selectedConfig: ConfBase) => {
  const base: any = {
    fields: [
      {
        name: conf.selector.name,
        type: conf.selector.type,
        label: conf.selector.label,
        options: conf.selector.options,
      },
    ],
  };

  const clone = {
    ...conf,
    fields: conf.fields
      ? base.fields.concat(selectedConfig.fields).concat(conf.fields)
      : base.fields.concat(selectedConfig.fields),
  };

  const { selector, ...newConfig } = clone;

  return newConfig;
};

export const translateListConf = (conf: ConfListBase) => {
  const fields = [
    {
      name: conf.input.name,
      type: conf.input.type,
      label: conf.input.label,
      helper_text: conf.input.helper_text,
    },
  ];

  const clone = {
    ...conf,
    fields: fields,
  };

  const { input, ...newConfig } = clone;

  return newConfig;
};
