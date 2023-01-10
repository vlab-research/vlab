import { useState } from 'react';
import { Form } from '../Form';

// const getFieldsFromOption = (selector: any, selectedOption: any) => {
//   const { fields } = selector.options.find(
//     (option: any) =>
//       createNameFor(option.title) === createNameFor(selectedOption.title)
//   );

//   return fields;
// };

const ConfigSelect = (props: any) => {
  const { config } = props;
  const { selector } = config;

  const base = {
    fields: [
      {
        name: selector.name,
        type: selector.type,
        label: selector.label,
        options: selector.options,
      },
    ],
  };

  const defaultConfig = base.fields[0].options[0];
  const [selectedConfig, setSelectedConfig] = useState(defaultConfig);
  const baseFields = base.fields;
  const dynamicFields = selectedConfig.fields;
  const joinedArray = baseFields.concat(dynamicFields);

  const findNestedConfig = (x: string) => {
    const el = base.fields[0].options.find((option: any) => option.title === x);
    setSelectedConfig(el);
  };

  return (
    <Form
      fields={joinedArray}
      setNestedConfig={(x: any) => findNestedConfig(x)}
      {...props}
    ></Form>
  );
};

export default ConfigSelect;
