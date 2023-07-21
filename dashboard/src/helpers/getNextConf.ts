import { isLastElement } from './arrays';

const getNextConf = (confs: any[], conf: any) => {
  if (isLastElement(confs, conf)) {
    return;
  }
  const i = confs.findIndex((c: string) => c === conf);
  return confs[i + 1];
};

export default getNextConf;
