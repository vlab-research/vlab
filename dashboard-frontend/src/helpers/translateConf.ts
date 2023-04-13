import { ConfSelectBase, ConfBase } from '../types/conf';

export const translateConf = (
  conf: ConfSelectBase,
  selectedConfig: ConfBase
) => {
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
