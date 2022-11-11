import { CreateStudyConfigData } from '../types/study';

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
          options: selector.options.map(
            (option: CreateStudyConfigData) => option
          ),
        },
      ],
    };
    return newConfig;
  }

  return config;
};
