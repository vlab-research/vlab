import { ConfSelect, ConfBase, ConfList } from '../types/conf';

export const mergeConfs = (conf: ConfSelect, selectedConf: ConfBase) => {
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
      ? base.fields.concat(selectedConf.fields).concat(conf.fields)
      : base.fields.concat(selectedConf.fields),
  };

  const { selector, ...newConfig } = clone;

  return newConfig;
};

export const translateListConf = (conf: ConfList, selectedConf?: any) => {
  const fields = [
    {
      name: conf.input.name,
      type: conf.input.type,
      label: conf.input.label,
      helper_text: conf.input.helper_text ?? conf.input.helper_text,
      options: conf.input.options ?? conf.input.options,
      conf: conf.input.conf ? mergeConfs(conf.input.conf, selectedConf) : null,
    },
  ];

  const clone = {
    ...conf,
    fields: fields,
  };

  const { input, ...newConfig } = clone;

  return newConfig;
};
