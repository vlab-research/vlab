import { useEffect, useState } from 'react';
import { ConfBase, FieldState } from '../../../../types/conf';
import { DataEvent, EventInterface } from '../../../../types/form';
import list from '../../../StudyConfPage/controllers/list';
import select from '../../../StudyConfPage/controllers/select';
import simple from '../../../StudyConfPage/controllers/simple';
import { getFormData } from '../../../../helpers/getFormData';

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
  const [fieldState, setState] = useState<FieldState[] | any>();

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
      value: e.value ?? e.value,
    };

    // controller creates state and creates "newLocalFormData"
    // const [newState, newLocalFormData] = controller(conf, localFormData, event, state);
    const newState = controller(conf, localFormData, event, fieldState);

    const newLocalFormData = getFormData(conf, fieldState);

    // state is a local concept, only the Fieldset needs to care about it
    setState(newState);

    // Send form data to form, that's all it cares about
    handleChange(newLocalFormData);
  };

  if (!fieldState) return null;

  return (
    <>
      {fieldState.map((f: FieldState | any, i: number) => {
        const { component: Component, ...props } = f;

        return (
          <Component
            key={`${f.name}-${i}`}
            onChange={(e: any) => onChange(`${f.name}-${i}`, f.type, e)}
            error={error}
            {...props}
          />
        );
      })}
    </>
  );
};

export default Fieldset;
