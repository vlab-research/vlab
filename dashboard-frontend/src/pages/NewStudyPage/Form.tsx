import { useMemo, useState, useEffect } from 'react';
import { translator } from '../../helpers/translator';
import { getFormFields } from '../../helpers/getFormFields';
import { createInitialState } from '../../helpers/createState';
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

export const Form = ({ config, getFormData, isLast, setIndex, title }: any) => {
  const translatedConfig = useMemo(() => {
    return translator(config);
  }, [config]);

  const { fields } = translatedConfig;

  const dynamicFields = useMemo(() => {
    return fields && getFormFields(fields);
  }, [fields]);

  if (!fields) {
    throw new Error('You are calling Renderer with no fields.');
  }

  const fieldsWithProps = dynamicFields && mapPropsToFields(dynamicFields);

  const initialState = useMemo(() => {
    return createInitialState(translatedConfig);
  }, [translatedConfig]);

  const [partialFormData, setPartialFormData] = useState(initialState);

  useEffect(() => {
    setPartialFormData(initialState);
  }, [initialState]);

  const handleSubmit = (e: any) => {
    e.preventDefault();
    getFormData(partialFormData);

    if (isLast) {
      return;
    }
    setIndex((prevCount: number) => addOne(prevCount));
  };

  const renderComponents = (items: any[]) => {
    return items.map(item => {
      const { Component, ...props } = item;
      const { name } = props;

      const handleChange = (x: any) => {
        setPartialFormData({ ...partialFormData, [name]: x });
      };

      return (
        <Component
          key={name}
          config={config}
          {...props}
          onChange={handleChange}
        />
      );
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
                    {title}
                  </h3>
                  {fieldsWithProps && renderComponents(fieldsWithProps)}
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
