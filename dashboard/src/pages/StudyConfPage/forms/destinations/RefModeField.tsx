import React from 'react';
import { GenericSelect, SelectI } from '../../components/Select';
import {
  REF_MODE_CHANGE_WARNING,
  displayedRefMode,
  refModeChanges,
  refModeOptions,
} from './refMode';

const Select = GenericSelect as SelectI<any>;

interface Props {
  data: any;
  handleChange: (e: any) => void;
  // The destination as saved, absent for one being added now. It is the conf
  // rather than its mode because a conf saved before the field existed has no
  // mode to pass, and that conf has ads in flight like any other.
  saved?: any;
}

// One control, rendered by all five destination forms rather than copied into
// each, so that a multi-channel study attributes exactly one way.
const RefModeField: React.FC<Props> = ({ data, handleChange, saved }: Props) => {
  const warn = !!saved && refModeChanges(saved.ref_mode, data.ref_mode);

  return (
    <>
      <Select
        name="ref_mode"
        label="Where does this ad's stratum data end up?"
        options={refModeOptions()}
        handleChange={handleChange}
        value={displayedRefMode(data.ref_mode)}
      />
      {warn && (
        <p className="my-2 text-sm text-red-700">{REF_MODE_CHANGE_WARNING}</p>
      )}
    </>
  );
};

export default RefModeField;
