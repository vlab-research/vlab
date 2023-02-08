import { ConfigBase } from '../types/form';
import { createNameFor } from './strings';

export const mapDestinations = (config: ConfigBase) => {
  const { selector } = config;

  return selector?.options.map((option: ConfigBase) => {
    return { name: createNameFor(option.title), label: option.title };
  });
};

export default mapDestinations;
