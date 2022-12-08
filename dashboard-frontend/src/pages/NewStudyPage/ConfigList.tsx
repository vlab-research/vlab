import { Fragment } from 'react';
import PrimaryButton from '../../components/PrimaryButton';
import ConfigSelect from './ConfigSelect';

const ConfigList = ({ config, ...props }: any) => {
  const { callToAction } = props;

  const arr = [1];

  return arr.map(() => {
    return (
      <Fragment>
        <ConfigSelect config={config} {...props}></ConfigSelect>
        <PrimaryButton>{callToAction}</PrimaryButton>
      </Fragment>
    );
  });
};

export default ConfigList;
