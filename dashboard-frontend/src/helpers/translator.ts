import { CreateStudyConfigData } from '../types/study';
import { createNameFor } from './strings';

export const translator = (config: any) => {
  const { type, title, description, selector } = config;
  if (type === 'config-select' || type === 'config-multi') {
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
