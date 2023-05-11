import React from 'react';

interface Props {
  id: string;
  component: React.FC<any>;
  data: any;
  callback?: (arg: any) => void;
}
const Form: React.FC<Props> = (props: Props) => {
  const { id, component, data, callback } = props;

  const renderFormTemplate = () => {
    const form = {
      id,
      data,
      Component: component,
      callback,
    };
    const { Component, ...props } = form;

    return <Component {...props} />;
  };

  return renderFormTemplate();
};

export default Form;
