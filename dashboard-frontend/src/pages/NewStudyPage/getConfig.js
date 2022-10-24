import { translator } from '../../helpers/translator';

export const getConfig = config => {
  return config.fields
    ? config.fields.map(translator)
    : config.recruitment_simple.fields.map(translator); // TODO replace with dynamic config key
};
