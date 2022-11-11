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

export const Renderer = ({ config, erroroncreate, state, setState }) => {
  const translatedConfig = translator(config[1]);

  const fields = useMemo(() => {
    const { fields } = translatedConfig;
    return getFormFields(fields);
  }, [translatedConfig]);

  if (!fields) {
    throw new Error('You are calling Renderer with no fields.');
  }

  const fieldsWithProps = mapPropsToFields(fields);

  const renderComponents = items => {
    return items.map(item => {
      const { Component, ...props } = item;

      return (
        <Fragment key={props.name}>
          <Component
            config={config}
            fields={fields}
            {...props}
            erroroncreate={erroroncreate}
            state={state}
            setState={setState}
          />
        </Fragment>
      );
    });
  };

  return renderComponents(fieldsWithProps);
};
