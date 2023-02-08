import Button from '../pages/NewStudyPage/form/buttons/Button';
import List from '../pages/NewStudyPage/form/inputs/List';
import Select from '../pages/NewStudyPage/form/inputs/Select';
import Text from '../pages/NewStudyPage/form/inputs/Text';
import { ConfigBase, FieldBase } from '../types/form';
import { getInitialValue } from './getInitialValue';
import { createNameFor } from './strings';

const str: keyof FieldBase = 'type';

export const stateBuilder = (field: FieldBase) => {
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
    defaultValue: field.defaultValue ?? field.defaultValue,
    call_to_action: field.call_to_action ?? field.call_to_action,
    options: field.options?.map((option: ConfigBase | any) =>
      option.title
        ? {
            name: createNameFor(option.title),
            label: option.title,
            setNestedConfig: true,
          }
        : option
    ),
    value: getInitialValue(field, 'type'),
  };
};
