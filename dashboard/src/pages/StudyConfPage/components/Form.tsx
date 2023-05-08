import React from 'react';

interface Props {
  id: string;
  component: any;
  data: any;
}
const Form: React.FC<Props> = (props: Props) => {
  const { id, component, data } = props;

  const renderFormTemplate = () => {
    const form = {
      id,
      data,
      Component: component,
    };
    const { Component, ...props } = form;

    return <Component {...props} />;
  };

  return renderFormTemplate();
};

export default Form;
