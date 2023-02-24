import { Config } from '../types/form';

export const translateConfig = (
  config: Config,
  selectedConfig: Config | undefined
) => {
  const base: any = {
    fields: [
      {
        name: config?.selector?.name,
        type: config?.selector?.type,
        label: config?.selector?.label,
        options: config?.selector?.options,
      },
    ],
  };

  const clone = {
    ...config,
    fields: base.fields.concat(selectedConfig?.fields),
  };

  const { selector, ...newConfig } = clone;

  return newConfig;
};
