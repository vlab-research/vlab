import { useEffect, useState } from 'react';
import { reduceFieldStateToAnObject } from '../../../../helpers/arrays';
import {
  ConfBase,
  DataEvent,
  EventInterface,
  FieldState,
} from '../../../../types/form';
import list from '../../../StudyConfPage/controllers/list';
import select from '../../../StudyConfPage/controllers/select';
import simple from '../../../StudyConfPage/controllers/simple';

type Props = {
  conf: ConfBase;
  localFormData: any;
  handleChange: (e: DataEvent) => void;
  error: any;
};

const Fieldset: React.FC<Props> = ({
  conf,
  localFormData,
  handleChange,
  error,
}) => {
  const [state, setState] = useState<FieldState[]>();

  const str: keyof ConfBase = 'type';

  const type = conf[str];

  const lookup: any = {
    confObject: simple,
    confSelect: select,
    confList: list,
  };

  const controller = lookup[type];

  if (!controller) {
    throw new Error(`Could not find form for controller type: ${type}`);
  }

  useEffect(() => {
    setState(controller(conf, localFormData));
  }, [conf, controller, localFormData]);

  const onChange = (name: string, fieldType: string, e: DataEvent) => {
    const event: EventInterface = {
      name,
      fieldType,
      type: e.type,
      value: e.value,
    };

    // controller creates state and creates "newLocalFormData"
    // const [newState, newLocalFormData] = controller(conf, localFormData, event, state);
    const newState = controller(conf, localFormData, event, state);
    const newLocalFormData = reduceFieldStateToAnObject(newState);

    // state is a local concept, only the Fieldset needs to care about it
    setState(newState);

    // Send form data to form, that's all it cares about
    handleChange({ type: 'change', value: newLocalFormData });
  };

  if (!state) return null;

  return (
    <>
      {state.map(f => {
        const { component: Component, ...props } = f;

        return (
          <Component
            key={f.name}
            onChange={(e: any) => onChange(f.name, f.type, e)}
            error={error}
            {...props}
          />
        );
      })}
    </>
  );
};

export default Fieldset;
