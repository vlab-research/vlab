import TextInput from '../pages/NewStudyPage/TextInput';
import SelectInput from '../pages/NewStudyPage/Select';
import { toCamelCase } from './strings';

interface Obj {
  name: string;
  type: string;
  label: string;
  options?: Option[];
}

const str: keyof Obj = 'type';
interface Option {
  name: string;
}

export const translator = (obj: Obj) => {
  const lookup: any = {
    text: TextInput,
    select: SelectInput,
  };

  const type = obj[str];

  const component = lookup[type];

  if (!component) {
    throw new Error(`Could not find component for type: ${obj.type}`);
  }

  return {
    id: obj.name,
    name: toCamelCase(obj.name),
    type: type,
    component: component,
    label: obj.label,
    options: obj.options ?? obj.options,
  };
};
