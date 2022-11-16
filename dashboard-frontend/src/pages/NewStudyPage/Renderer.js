import { Fragment, useMemo } from 'react';
import { getFormFields } from '../../helpers/getFormFields';
import { translator } from '../../helpers/translator';

const mapPropsToFields = fields => {
  const fieldsWithProps = [];

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

export const Renderer = ({
  config,
  setCurrentConfig,
  erroroncreate,
  formData,
  setFormData,
}) => {
  const translatedConfig = translator(config);

  const fields = useMemo(() => {
    const { fields } = translatedConfig;

    return getFormFields(fields);
  }, [translatedConfig]);

  if (!fields) {
    throw new Error('You are calling Renderer with no fields.');
  }

  const fieldsWithProps = mapPropsToFields(fields);

  // user selects an option and state is updated at the child level
  // the state is passed back up to the parent
  // given some value from the state the renderer knows what to do with a new config
  // fields and props are updated to display a new config

  const renderComponents = items => {
    return items.map(item => {
      const { Component, ...props } = item;
      const { name } = props;

      return (
        <Fragment key={name}>
          <Component
            config={config}
            setCurrentConfig={setCurrentConfig}
            formData={formData}
            fields={fields}
            {...props}
            erroroncreate={erroroncreate}
          />
        </Fragment>
      );
    });
  };

  return renderComponents(fieldsWithProps);
};
