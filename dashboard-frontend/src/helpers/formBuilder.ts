import List from '../pages/NewStudyPage/inputs/List';
import Select from '../pages/NewStudyPage/inputs/Select';
import Text from '../pages/NewStudyPage/inputs/Text';
import { StudyFieldResource } from '../types/study';
import { createNameFor } from './strings';

const str: keyof StudyFieldResource = 'type';

export const formBuilder = (field: StudyFieldResource) => {
  const lookup: any = {
    text: Text,
    number: Text,
    select: Select,
    list: List,
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
    options: field.options?.map((option: any) =>
      option.title
        ? {
            name: createNameFor(option.title),
            label: option.title,
            setNestedConfig: true,
          }
        : option
    ),
  };
};
