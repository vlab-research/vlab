import { Fragment } from 'react';
import { mapPropsToFields } from './Form';

const ConfigObject = ({ config, setFormData, ...props }: any) => {
  const { fields } = config;

  const fieldsWithProps = fields && mapPropsToFields(fields);

  const renderComponents = (items: any[]) => {
    return (
      items &&
      items.map(item => {
        const { Component, ...props } = item;
        const { name } = props;

        return (
          <Fragment key={name}>
            <Component config={config} setFormData={setFormData} {...props} />
          </Fragment>
        );
      })
    );
  };

  return renderComponents(fieldsWithProps);
};

export default ConfigObject;
