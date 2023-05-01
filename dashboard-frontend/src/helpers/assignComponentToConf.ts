import General from '../pages/StudyConfPage/components/form/General';
import { createNameFor } from './strings';
import { ConfBase } from '../types/form';

const str: keyof ConfBase = 'title';

export const assignComponentToConf = (conf: ConfBase) => {
  const lookup: any = {
    general: General,
  };

  const title = createNameFor(conf[str]);

  const component: React.FunctionComponent<any> = lookup[title];

  if (!component) {
    throw new Error(`Could not find component for conf: ${conf.title}`);
  }

  return { Component: component, ...conf };
};
