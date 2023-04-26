import Text from '../pages/NewStudyPage/components/form/inputs/Text';
import Select from '../pages/NewStudyPage/components/form/inputs/Select';
import Button from '../pages/NewStudyPage/components/form/inputs/Button';
import Fieldset from '../pages/NewStudyPage/components/form/Fieldset';
import { ConfBase, FieldBase } from '../types/conf';
import { createNameFor } from './strings';

export const translateField = (field: FieldBase, localFormData?: any) => {
  const lookup: any = {
    text: Text,
    number: Text,
    select: Select,
    fieldset: Fieldset,
    button: Button,
  };

  const str: keyof FieldBase = 'type';

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
    label: field.label ?? field.label,
    helper_text: field.helper_text ?? field.helper_text,
    options: field.options?.map((option: ConfBase | any) =>
      option.title
        ? {
            name: createNameFor(option.title),
            label: option.title,
          }
        : option
    ),
    value: localFormData
      ? localFormData[field.name]
        ? localFormData[field.name]
        : localFormData
      : getInitialValue(field),
    conf: field.conf ? field.conf : null,
  };
};

export const getInitialValue = (f: FieldBase) => {
  let { type } = f;

  switch (true) {
    case type === 'text':
      return '';
    case type === 'select':
      return f.options && f.options[0].name
        ? f.options[0].name
        : createNameFor(f.options && f.options[0].title);
    case type === 'number':
      return 1;
    case type === 'fieldset':
      return [];
    case type === 'button':
      return '';
    default:
      console.log('Field type does not exist');
  }
};
