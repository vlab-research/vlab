import { Fragment, useMemo } from 'react';
import { getFormFields } from '../../helpers/getFormFields';
import { translator } from '../../helpers/translator';

export const mapPropsToFields = fields => {
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

export const Renderer = ({ config, erroroncreate }) => {
  const translatedConfig = translator(config);

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
      const { name } = props;

      return (
        <Fragment key={name}>
          <Component config={config} {...props} erroroncreate={erroroncreate} />
        </Fragment>
      );
    });
  };

  return renderComponents(fieldsWithProps);
};
