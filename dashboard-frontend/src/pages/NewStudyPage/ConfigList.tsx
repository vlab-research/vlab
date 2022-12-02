import React, { useCallback, useState } from 'react';
import Text from './inputs/Text';
import ConfigSelect from './ConfigSelect';
import List from './inputs/List';
// import { PlusCircleIcon } from '@heroicons/react/solid';
// import PrimaryButton from '../../components/PrimaryButton';

const ConfigList = ({ config, ...props }: any) => {
  const { id, label, options } = props;
  const { selector } = config;
  const { callToAction } = selector;

  return (
    <React.Fragment>
      {/* <ConfigSelect {...props}></ConfigSelect> */}
      <Text {...props}></Text>
      <List {...props}></List>
    </React.Fragment>
  );
};

export default ConfigList;
