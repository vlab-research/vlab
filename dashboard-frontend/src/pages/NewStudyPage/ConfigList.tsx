import { Fragment } from 'react';
import PrimaryButton from '../../components/PrimaryButton';
import ConfigSelect from './ConfigSelect';
// import List from './inputs/List';

const ConfigList = ({ config, onChange, ...props }: any) => {
  const { calltoaction } = props;

  // const arr = [1];

  const handleClick = () => {};

  // return arr.map(() => {
  return (
    <Fragment>
      <ConfigSelect
        config={config}
        onChange={onChange}
        {...props}
      ></ConfigSelect>
      <PrimaryButton onClick={() => handleClick()}>
        {calltoaction}
      </PrimaryButton>
    </Fragment>
  );
  // });
};

export default ConfigList;
