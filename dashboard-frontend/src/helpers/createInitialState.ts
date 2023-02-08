import { ConfigBase } from '../types/form';
import { stateBuilder } from './stateBuilder';

// global
export const createInitialState = (config: ConfigBase) => {
  return config.fields?.map(stateBuilder);
};
