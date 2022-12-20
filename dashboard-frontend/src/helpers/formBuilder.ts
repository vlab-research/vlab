import ConfigList from '../pages/NewStudyPage/ConfigList';
import ConfigObject from '../pages/NewStudyPage/ConfigObject';
import ConfigSelect from '../pages/NewStudyPage/ConfigSelect';
import List from '../pages/NewStudyPage/inputs/List';
import Select from '../pages/NewStudyPage/inputs/Select';
import Text from '../pages/NewStudyPage/inputs/Text';
import { StudyFieldResource } from '../types/study';
import { checkPropertiesExist } from './objects';
import { jsonTranslator } from './translator';

const str: keyof StudyFieldResource = 'type';

export const formBuilder = (field: StudyFieldResource) => {
  const lookup: any = {
    text: Text,
    number: Text,
    select: Select,
    list: List,
    configSelect: ConfigSelect,
    configList: ConfigList,
    configObject: ConfigObject,
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
    helpertext: field.helpertext ?? field.helpertext,
    defaultValue: field.defaultValue ?? field.defaultValue,
    calltoaction: field.calltoaction ?? field.calltoaction,
    options:
      field.options &&
      field.options.some((option: any) =>
        checkPropertiesExist(option, 'label', 'name')
      )
        ? field.options
        : field.options?.map((option: any) => jsonTranslator(option)),
  };
};
