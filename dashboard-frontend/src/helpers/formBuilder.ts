import Button from '../pages/NewStudyPage/form/buttons/Button';
import List from '../pages/NewStudyPage/form/inputs/List';
import Select from '../pages/NewStudyPage/form/inputs/Select';
import Text from '../pages/NewStudyPage/form/inputs/Text';
import { FieldBase } from '../types/form';
import { Config } from '../types/form';
import { createNameFor } from './strings';

const str: keyof FieldBase = 'type';

export const formBuilder = (field: FieldBase) => {
  const lookup: any = {
    text: Text,
    number: Text,
    select: Select,
    list: List,
    button: Button,
  };

  const type = field[str];

  const component = lookup[type];

  if (!component) {
    throw new Error(`Could not find component for type: ${field.type}`);
  }

  return {
    id: field.name,
    name: field.name,
    type: type,
    component: component,
    label: field.label,
    helper_text: field.helper_text ?? field.helper_text,
    call_to_action: field.call_to_action ?? field.call_to_action,
    options: field.options?.map((option: Config | any) =>
      option.title
        ? {
            name: createNameFor(option.title),
            label: option.title,
          }
        : option
    ),
    value: getInitialValue(field),
  };
};

export const getInitialValue = (obj: FieldBase) => {
  let { type } = obj;

  switch (true) {
    case type === 'text':
      return '';
    case type === 'select':
      return obj.options && obj.options[0].name
        ? obj.options[0].name
        : createNameFor(obj.options && obj.options[0].title);
    case type === 'number':
      return 0;
    case type === 'list':
      return [];
    case type === 'button':
      return '';
    default:
      console.log('Field type does not exist');
  }
};
