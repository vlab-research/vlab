import { useState } from 'react';
import { getFormFields } from '../../helpers/getFormFields';
import { addOne } from '../../helpers/numbers';
import PrimaryButton from '../../components/PrimaryButton';

export const mapPropsToFields = (fields: any[]) => {
  const fieldsWithProps: any[] = [];

  fields.forEach(field => {
    if (field.component) {
      const { component, ...props } = field;

      fieldsWithProps.push({
        ...props,
        Component: component,
      });
    }
  });

  return fieldsWithProps;
};

export const Form = ({ fields, setNestedConfig, ...props }: any) => {
  const { config, setIndex, isLast, setFormData } = props;

  if (!fields) {
    throw new Error('You are calling form with no fields.');
  }

  const formFields = getFormFields(fields);
  const fieldsWithProps = formFields && mapPropsToFields(formFields);
  const [partialFormData, setPartialFormData] = useState({});

  const handleSubmit = (e: any) => {
    e.preventDefault();

    if (!isLast) {
      setIndex((prevCount: number) => addOne(prevCount));
    }

    setFormData(partialFormData);
  };

  const renderFields = (fields: any[]) => {
    return fields.map(field => {
      const { Component, ...props } = field;
      const { name, type } = props;

      const handleChange = (x: any) => {
        setPartialFormData({ ...partialFormData, [name]: x });

        // this means check if the field is a select component AND has the setNestedConfig property
        // if yes then invoke the callback
        // if no i.e. the field is a text field OR the select field is a regular select field then do not run
        // we don't want the nested config to run on every input change!!
        type === 'select' &&
          field.options.forEach(
            (option: any) => option.setNestedConfig && setNestedConfig(x)
          );
      };

      return <Component key={name} {...props} onChange={handleChange} />;
    });
  };

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <form onSubmit={handleSubmit}>
          <div className="shadow overflow-hidden sm:rounded-md">
            <div className="px-4 py-5 bg-white sm:p-6">
              <div className="grid grid-cols-6 gap-6">
                <div className="col-span-6 sm:col-span-5">
                  <h3 className="text-lg font-medium leading-6 text-gray-900">
                    {config.title} {`I am a ${config.type}`}
                  </h3>
                  {fieldsWithProps && renderFields(fieldsWithProps)}
                </div>
              </div>
            </div>
            <div className="px-4 py-3 bg-gray-50 text-right sm:px-6">
              {!isLast ? (
                <PrimaryButton type="submit" testId="new-study-next-button">
                  Next
                </PrimaryButton>
              ) : (
                <PrimaryButton type="submit" testId="new-study-submit-button">
                  Create
                </PrimaryButton>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
