import ListInput from '../pages/NewStudyPage/inputs/List';
import SelectInput from '../pages/NewStudyPage/inputs/Select';
import TextInput from '../pages/NewStudyPage/inputs/Text';
import { checkPropertiesExist } from './objects';
import { jsonTranslator } from './translator';

interface Obj {
  name: string;
  type: string;
  label: string;
  helpertext?: string;
  options?: Option[];
}

interface Option {
  name: string;
  label: string;
}

const str: keyof Obj = 'type';

export const formBuilder = (obj: Obj) => {
  const lookup: any = {
    text: TextInput,
    number: TextInput,
    select: SelectInput,
    list: ListInput,
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
    helpertext: obj.helpertext ?? obj.helpertext,
    options:
      obj.options &&
      obj.options.some((option: Option) =>
        checkPropertiesExist(option, 'label', 'name')
      )
        ? obj.options
        : obj.options?.map((option: Option) => jsonTranslator(option)),
  };
};
