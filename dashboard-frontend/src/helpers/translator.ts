import { CreateStudyConfigData } from '../types/study';
import { createNameFor } from './strings';

export const translator = (config: any) => {
  const { type, title, description, selector, fields, list } = config;

  const getFields = () => {
    const mapped = fields.map(({ name, type, label, helperText }: any) => ({
      name: name,
      type: type,
      label: label,
      helperText: helperText,
    }));
    return Object.assign({}, ...mapped);
  };

  if (type === 'config-multi') {
    const newConfig = {
      type,
      title,
      description,
      list,
      fields: [
        {
          name: selector.name,
          type: selector.type,
          label: selector.label,
          options: selector.options.map((option: CreateStudyConfigData) => {
            return {
              name: createNameFor(option.title),
              label: option.title,
            };
          }),
        },
        fields && getFields(),
      ],
    };
    return newConfig;
  }
  if (type === 'config-select') {
    const newConfig = {
      type,
      title,
      description,
      fields: [
        {
          name: selector.name,
          type: selector.type,
          label: selector.label,
          options: selector.options.map((option: CreateStudyConfigData) => {
            return {
              name: createNameFor(option.title),
              label: option.title,
            };
          }),
        },
      ],
    };
    return newConfig;
  }
  return config;
};

export const jsonTranslator = (json: any) => {
  const { name, code } = json;

  const newObj = {
    name: code,
    label: name,
  };

  return newObj;
};
