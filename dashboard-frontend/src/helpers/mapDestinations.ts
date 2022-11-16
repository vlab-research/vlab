import { CreateStudyConfigData } from '../types/study';
import { createNameFor } from './strings';

export const mapDestinations = (config: CreateStudyConfigData) => {
  const { selector } = config;

  return selector.options.map((option: any) => {
    return { name: createNameFor(option.title), label: option.title };
  });
};

export default mapDestinations;
