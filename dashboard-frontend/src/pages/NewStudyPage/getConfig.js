import { translator } from '../../helpers/translator';

export const getConfig = config => {
  return config.fields.map(translator);
};
