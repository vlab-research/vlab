import React from 'react';
import {
  CreateStudy as StudyType,
  GlobalFormData,
  LocalFormData,
} from '../types/conf';

interface Props {
  id: string;
  component: any;
  globalData: GlobalFormData;
  localData: LocalFormData;
  study: StudyType;
  confKeys: string[];
}
const Form: React.FC<Props> = (props: Props) => {
  const { component: Component, ...childProps } = props;
  return <Component {...childProps} />;
};

export default Form;
