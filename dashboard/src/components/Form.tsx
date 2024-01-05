import React from 'react';
import {
  CreateStudy as StudyType,
  GlobalFormData,
  LocalFormData,
} from '../types/conf';

import { Account } from '../types/account';

interface Props {
  id: string;
  component: any;
  globalData: GlobalFormData;
  localData: LocalFormData;
  facebookAccount: Account;
  study: StudyType;
}
const Form: React.FC<Props> = (props: Props) => {
  const { component: Component, ...childProps } = props;
  return <Component {...childProps} />;
};

export default Form;
