import { Config } from '../types/form';
import { createNameFor } from './strings';

export const mapDestinations = (config: Config) => {
  const { selector } = config;

  return selector?.options.map((option: Config) => {
    return { name: createNameFor(option.title), label: option.title };
  });
};

export default mapDestinations;
