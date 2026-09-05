import React from 'react';
import { RadioGroup } from '../../components/RadioGroup';
import {
  REF_MODE_CHANGE_WARNING,
  REF_MODE_LABEL,
  displayedRefMode,
  refModeChanges,
  refModeOptions,
} from './refMode';

interface Props {
  data: any;
  // Position in the study's destination list. Makes the radio group's DOM
  // name unique per destination; without it every destination's radios are
  // one browser-level group and only one destination can hold a choice.
  index: number;
  handleChange: (e: any) => void;
  // The destination as saved, absent for one being added now. It is the conf
  // rather than its mode because a conf saved before the field existed has no
  // mode to pass, and that conf has ads in flight like any other.
  saved?: any;
}

// One control, rendered by all five destination forms rather than copied into
// each, so that a multi-channel study attributes exactly one way.
//
// Radios rather than a select: the two options are terms the researcher is
// being taught -- "plain ref" and "encoded ref" -- and a term is useless
// without the sentence that defines it. An `<option>` can hold a name or an
// explanation, never both, which is how this control ended up as a question
// answered by two sentences with no names at all. See `refMode.ts`.
const RefModeField: React.FC<Props> = ({
  data,
  index,
  handleChange,
  saved,
}: Props) => {
  const warn = !!saved && refModeChanges(saved.ref_mode, data.ref_mode);

  return (
    <>
      <RadioGroup
        name={`ref_mode-${index}`}
        fieldName="ref_mode"
        label={REF_MODE_LABEL}
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
