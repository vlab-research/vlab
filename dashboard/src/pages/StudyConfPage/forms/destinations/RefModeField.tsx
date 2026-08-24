import React, { useRef } from 'react';
import { GenericSelect, SelectI } from '../../components/Select';
import {
  REF_MODE_FLIP_WARNING,
  displayedRefMode,
  refModeConsequence,
  refModeOptions,
  refModeWouldChange,
} from './refMode';

const Select = GenericSelect as SelectI<any>;

interface Props {
  /** This destination's stored mode. Absent is a real state — see refMode.ts. */
  refMode?: string;
  handleChange: (e: any) => void;
}

/**
 * How this destination's ads carry attribution.
 *
 * Shared by every destination form rather than copied into each, because the
 * modes must not drift between channels — the point of offering both
 * everywhere is that a multi-channel study attributes exactly one way, and a
 * copy of this control per form is how that stops being true.
 *
 * The select is valued by `displayedRefMode`, which reports what a conf
 * actually does rather than what the form would default to. It emits `ref_mode`
 * into the conf only when the user changes it, so opening a legacy destination
 * and editing something else leaves its absent `ref_mode` absent. That is the
 * whole of the migration safety: see refMode.ts and
 * planning/ref-mode-dashboard-ux.md §4.3.
 */
const RefModeField: React.FC<Props> = ({ refMode, handleChange }: Props) => {
  // What this destination was loaded with, captured once. The flip warning is
  // about diverging from what the study's ads were BUILT with, so it has to
  // compare against the mode at mount, not against the previous keystroke.
  const loadedMode = useRef(refMode);

  const current = displayedRefMode(refMode);
  const options = refModeOptions();
  const wouldChange = refModeWouldChange(loadedMode.current, refMode);

  return (
    <div className="sm:my-4">
      <Select
        name="ref_mode"
        options={options}
        handleChange={handleChange}
        value={current}
        label="How should this ad carry attribution?"
      />
      <p className="mt-1 text-sm text-gray-500 w-4/5">
        {refModeConsequence(current)}
      </p>
      {wouldChange && (
        <div className="mt-2 w-4/5 rounded-md border-l-4 border-amber-400 bg-amber-50 p-3">
          <p className="text-sm text-amber-800">{REF_MODE_FLIP_WARNING}</p>
        </div>
      )}
    </div>
  );
};

export default RefModeField;
