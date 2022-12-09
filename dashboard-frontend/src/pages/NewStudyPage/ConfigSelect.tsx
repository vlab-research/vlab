import { Fragment, useCallback, useMemo, useState } from 'react';
import { getFormFields } from '../../helpers/getFormFields';
import Select from './inputs/Select';
import { mapPropsToFields } from './Renderer';

const ConfigSelect = ({ config, setFormData, ...props }: any) => {
  const { options, defaultValue } = props;
  const { selector } = config;

  const [selectedConfig, setSelectedConfig] = useState({
    name: defaultValue ? '' : options[0].name,
    label: defaultValue ? defaultValue : options[0].label,
  });

  const fields = useMemo(() => {
    const { fields } = config;
    return fields && getFormFields(fields);
  }, [config]);

  const findNestedConfig = useCallback(() => {
    const index = options.findIndex(
      (option: any) => option.name === selectedConfig.name
    );
    return selector?.options[index];
  }, [options, selectedConfig, selector]);

  const nestedFields = useMemo(() => {
    const { fields } = findNestedConfig();
    return fields && getFormFields(fields);
  }, [findNestedConfig]);

  const parentProps = fields && mapPropsToFields(fields);
  const childProps = nestedFields && mapPropsToFields(nestedFields);

  const renderComponents = (items: any[]) => {
    return (
      items &&
      items.map(item => {
        const { Component, ...childProps } = item;
        const { name } = childProps;

        return (
          <Fragment key={name}>
            <Component
              config={config}
              setFormData={setFormData}
              {...childProps}
            />
          </Fragment>
        );
      })
    );
  };

  return (
    <>
      <Select {...props} setSelectedConfig={setSelectedConfig}></Select>
      {renderComponents(childProps)}
      {renderComponents(parentProps)}
    </>
  );
};

export default ConfigSelect;
