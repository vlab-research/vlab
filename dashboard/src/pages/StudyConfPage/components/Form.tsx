import React from 'react';
import { LocalFormData } from '../../../types/conf';

interface Props {
  id: string;
  data: LocalFormData;
  component: React.FC<any>;
}
const Form: React.FC<Props> = (props: Props) => {
  const { id, data, component } = props;

  const form = {
    id,
    data,
    Component: component,
  };
  const { Component, ...childProps } = form;

  return <Component {...childProps} />;
};

export default Form;
