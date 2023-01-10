import { useRef, useState } from 'react';
import PrimaryButton from '../../../components/PrimaryButton';
import { reorderArray } from '../../../helpers/arrays';
import { getFormFields } from '../../../helpers/getFormFields';
import { addOne } from '../../../helpers/numbers';
import { mapPropsToFields } from '../Form';
import List from '../inputs/List';

// reimagine configList as multiple forms rather than one single form
// configList = [<form>, <form>, <form>]

const ConfigList = (props: any) => {
  const { config, setIndex, isLast, setFormData } = props;
  const { selector, fields, list_label, call_to_action, list_ref } = config;

  // using list_ref find the target field from the config
  // once found we take the corresponding data for that field from the state
  // we can find it by accessing the partialFormData object
  // once we have the data we push the object to the savedForms array
  // we can then extract whatever prop we need in the List component to render the name of each saved list item
  // e.g. Fly2, test

  const base = {
    fields: [
      {
        name: selector.name,
        type: selector.type,
        label: selector.label,
        options: selector.options,
      },
      ...fields,
    ],
  };

  const defaultConfig = base.fields[0].options[0];

  const [selectedConfig, setSelectedConfig] = useState(defaultConfig);

  const baseFields = base.fields;
  const dynamicFields = selectedConfig.fields;
  const joinedArray = baseFields.concat(dynamicFields);

  // reorderArray() pushes the outer/parent fields to the end of the array so nested fields can come first
  const allFields = reorderArray(joinedArray, 1, 1);
  const formFields = getFormFields(allFields);
  const fieldsWithProps = formFields && mapPropsToFields(formFields);

  const findNestedConfig = (x: string) => {
    const el = base.fields[0].options.find((option: any) => option.title === x);
    setSelectedConfig(el);
  };

  const [partialFormData, setPartialFormData] = useState<any>({});
  const [listItems, setList] = useState<any[]>([]);
  const [count, setCount] = useState<number>(1);
  const savedForms = Array(count).fill(0);

  console.log(partialFormData);

  const handleSubmit = (e: any) => {
    e.preventDefault();
    setList([...listItems, partialFormData]);
    setFormData(listItems);
  };

  const renderFields = (fields: any[]) => {
    return fields.map(field => {
      const { Component, ...props } = field;
      const { name, type } = props;

      const handleChange = (x: any) => {
        setPartialFormData({ ...partialFormData, [name]: x });
        type === 'select' &&
          field.options.forEach(
            (option: any) => option.setNestedConfig && findNestedConfig(x)
          );
      };

      return <Component key={name} {...props} onChange={handleChange} />;
    });
  };

  const formRef: any = useRef();

  const focusForm = () => {
    formRef?.current.focus();
  };

  const handleClick = () => {
    if (!isLast) {
      setIndex((prevCount: number) => addOne(prevCount));
    }
  };

  const renderForms = (arr: any[]) => {
    return arr.map((el, index) => {
      return (
        <form onSubmit={handleSubmit} key={index} ref={formRef}>
          <div className="shadow overflow-hidden sm:rounded-md">
            <div className="px-4 py-5 bg-white sm:p-6">
              <div className="grid grid-cols-6 gap-6">
                <div className="col-span-6 sm:col-span-5">
                  <h3 className="text-lg font-medium leading-6 text-gray-900">
                    {config.title} {`I am a ${config.type}`}
                  </h3>
                  {fieldsWithProps && renderFields(fieldsWithProps)}
                  <PrimaryButton type="submit" testId="new-study-next-button">
                    {selector.call_to_action}
                  </PrimaryButton>
                </div>
              </div>
            </div>
          </div>
        </form>
      );
    });
  };

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        {renderForms(savedForms)}
        <div className="px-4 py-3 bg-gray-50 sm:px-6">
          <List
            list_label={list_label}
            call_to_action={call_to_action}
            setCount={setCount}
            savedForms={savedForms}
          ></List>
          <div className="px-4 py-3 bg-gray-50 text-right sm:px-6">
            {!isLast ? (
              <PrimaryButton
                onClick={handleClick}
                type="button"
                testId="new-study-next-button"
              >
                Next
              </PrimaryButton>
            ) : (
              <PrimaryButton
                onClick={handleClick}
                type="button"
                testId="new-study-submit-button"
              >
                Create
              </PrimaryButton>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConfigList;
