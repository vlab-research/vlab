import Text from '../pages/NewStudyPage/components/form/inputs/Text';
import Select from '../pages/NewStudyPage/components/form/inputs/Select';
import { FieldBase } from '../types/form';
import { createNameFor } from './strings';
import { Conf } from '../types/conf';

const str: keyof FieldBase = 'type';

export const translateField = (field: FieldBase, localFormData?: any) => {
  const lookup: any = {
    text: Text,
    number: Text,
    select: Select,
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
    options: field.options?.map((option: Conf | any) =>
      option.title
        ? {
            name: createNameFor(option.title),
            label: option.title,
          }
        : option
    ),
    value: localFormData ? localFormData[field.name] : getInitialValue(field),
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
      return 1;
    default:
      console.log('Field type does not exist');
  }
};
