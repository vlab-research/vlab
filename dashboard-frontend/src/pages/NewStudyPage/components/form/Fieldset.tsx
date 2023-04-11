import { FieldState } from '../../../../types/form';
import { useState, useEffect } from 'react';
import { reduceFieldStateToAnObject } from '../../../../helpers/arrays';

type Props = {
  controller: any;
  conf: any;
  localFormData: any;
  handleChange: any;
  error_message: any;

};

// Fieldset is now inception ready - you can have a fieldset inside your fieldset
// because it kicks out (handleChange) pure data, you can have that nest.
const Fieldset: React.FC<Props> = ({ handleChange, error_message, controller, conf, localFormData }) => {

  // FieldState[] is the state of a FieldSet
  const [state, setState] = useState<FieldState[]>();


  useEffect(() => {
    setState(controller(conf, localFormData));
  }, [conf, controller, localFormData]);


  const onChange = (name: any, fieldType: any, e: any) => {

    const event = {
      name,
      fieldType,
      type: e.type,
      value: fieldType === 'number' ? e.target.valueAsNumber : e.target.value,
    };

    // controller creates state and creates "newLocalFormData"
    // const [newState, newLocalFormData] = controller(conf, localFormData, event, state);
    const newState = controller(conf, localFormData, event, state);
    const newLocalFormData = reduceFieldStateToAnObject(newState)

    // state is a local concept, only the Fieldset needs to care about it
    setState(newState);

    // Send form data to form, that's all it cares about
    handleChange(newLocalFormData)
  }

  if (!state) return null

  return (
    <>
      {state.map(f => {
        const { component: Component, ...props } = f;

        return (
          <Component
            key={f.name}
            onChange={(e: any) => onChange(f.name, f.type, e)}
            error_message={error_message}
            {...props}
          />
        )
      })}

    </>

  )
}

export default Fieldset;
