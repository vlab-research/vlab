import { Fragment, useCallback, useMemo, useState } from 'react';
import { getFormFields } from '../../helpers/getFormFields';
import Select from './inputs/Select';
import { mapPropsToFields } from './Renderer';

const ConfigSelect = ({ config, ...props }: any) => {
  const { options, defaultValue } = props;
  const { selector } = config;

  const [selectedOption, setSelectedOption] = useState({
    name: defaultValue ? '' : options[0].name,
    label: defaultValue ? defaultValue : options[0].label,
  });

  const findNestedConfig = useCallback(() => {
    const index = options.findIndex(
      (option: any) => option.name === selectedOption.name
    );
    return selector?.options[index];
  }, [options, selectedOption, selector]);

  const fields = useMemo(() => {
    const { fields } = findNestedConfig();

    return getFormFields(fields);
  }, [findNestedConfig]);

  const fieldsWithProps = mapPropsToFields(fields);

  const renderComponents = (items: any[]) => {
    return items.map(item => {
      const { Component, ...childProps } = item;
      const { name } = childProps;

      return (
        <Fragment key={name}>
          <Component config={config} {...childProps} />
        </Fragment>
      );
    });
  };

  return (
    <>
      {' '}
      <Select
        {...props}
        selectedOption={selectedOption}
        setSelectedOption={setSelectedOption}
      ></Select>
      {renderComponents(fieldsWithProps)}
    </>
  );
};

export default ConfigSelect;
