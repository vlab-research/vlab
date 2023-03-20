import { Fragment, useEffect, useState } from 'react';
import { reducer } from '../../../../helpers/objects';
import Fieldset from './Fieldset';
import Submit from './buttons/Submit';
import { FieldState } from '../../../../types/form';
import { createNameFor } from '../../../../helpers/strings';
import useCreateStudy from '../../useCreateStudy';

export const Form = (props: any) => {
  const { config, controller, isLast, isCreateStudyForm, setIndex } = props;

  const { createStudy } = useCreateStudy();

  const [globalState, setGlobalState] = useState<FieldState[]>();

  const [formData, setFormData] = useState<any>({});

  useEffect(() => {
    setGlobalState(controller(config));
  }, [config, controller]);

  const title = createNameFor(config.title);

  const handleChange = (name: string, e: any) => {
    const event = {
      name,
      type: e.type,
      value: e.target.value,
    };

    const newState = controller(config, globalState, event);
    setGlobalState(newState);

    const state = globalState && reducer(globalState);

    const updateFormData = (x: any) => {
      setFormData({ ...formData, [title]: x });
    };

    updateFormData(state);
  };

  const handleSubmit = (e: any) => {
    e.preventDefault();

    if (!isLast) {
      setIndex((prevCount: number) => prevCount + 1);
    }

    createStudy(formData[title]);
  };

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <form onSubmit={handleSubmit}>
          {globalState && (
            <Fragment>
              <Fieldset
                globalState={globalState}
                handleChange={handleChange}
                {...props}
              ></Fieldset>
            </Fragment>
          )}
          <Submit
            isLast={isLast}
            isCreateStudyForm={isCreateStudyForm}
          ></Submit>
        </form>
      </div>
    </div>
  );
};

export default Form;
