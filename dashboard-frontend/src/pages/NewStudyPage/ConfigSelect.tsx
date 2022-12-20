import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import { getFormFields } from '../../helpers/getFormFields';
import Select from './inputs/Select';
import { mapPropsToFields } from './Form';

const ConfigSelect = ({ config, onChange, ...props }: any) => {
  const { selector } = config;
  const { options } = props;
  const defaultConfig = options[0].name;

  const [selectedOption, setSelectedOption] = useState(defaultConfig);

  useEffect(() => {
    setSelectedOption(defaultConfig);
  }, [defaultConfig]);

  const fields = useMemo(() => {
    const { fields } = config;
    return fields && getFormFields(fields);
  }, [config]);

  const findNestedConfig = useCallback(() => {
    const index = options.findIndex(
      (option: any) => option.name === selectedOption
    );
    return selector?.options[index];
  }, [options, selectedOption, selector]);

  const nestedFields = useMemo(() => {
    const { fields } = findNestedConfig();
    return fields && getFormFields(fields);
  }, [findNestedConfig]);

  const parentProps = fields && mapPropsToFields(fields);
  const childProps = nestedFields && mapPropsToFields(nestedFields);

  const [partialFormData, setPartialFormData] = useState({});

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
              {...childProps}
              onChange={(x: any) =>
                setPartialFormData({ ...partialFormData, [name]: x })
              }
            />
          </Fragment>
        );
      })
    );
  };

  return (
    <>
      <Select {...props} onChange={onChange}></Select>
      {renderComponents(childProps)}
      {renderComponents(parentProps)}
    </>
  );
};

export default ConfigSelect;
