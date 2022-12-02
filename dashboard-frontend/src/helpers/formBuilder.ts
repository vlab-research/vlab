import ConfigList from '../pages/NewStudyPage/ConfigList';
import ConfigSelect from '../pages/NewStudyPage/ConfigSelect';
import List from '../pages/NewStudyPage/inputs/List';
import Select from '../pages/NewStudyPage/inputs/Select';
import Text from '../pages/NewStudyPage/inputs/Text';
import { checkPropertiesExist } from './objects';
import { jsonTranslator } from './translator';

interface Obj {
  name: string;
  type: string;
  label: string;
  helperText?: string;
  defaultValue?: string;
  options?: Option[];
}

interface Option {
  name: string;
  label: string;
}

const str: keyof Obj = 'type';

export const formBuilder = (obj: Obj) => {
  const lookup: any = {
    text: Text,
    number: Text,
    select: Select,
    list: List,
    configSelect: ConfigSelect,
    configList: ConfigList,
  };

  const type = obj[str];

  const component = lookup[type];

  if (!component) {
    throw new Error(`Could not find component for type: ${obj.type}`);
  }

  return {
    id: obj.name,
    name: obj.name,
    type: type,
    component: component,
    label: obj.label,
    helperText: obj.helperText ?? obj.helperText,
    defaultValue: obj.defaultValue ?? obj.defaultValue,
    options:
      obj.options &&
      obj.options.some((option: Option) =>
        checkPropertiesExist(option, 'label', 'name')
      )
        ? obj.options
        : obj.options?.map((option: Option) => jsonTranslator(option)),
  };
};
