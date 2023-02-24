import { Fragment, useEffect, useState } from 'react';
import { reducer } from '../../../../helpers/objects';
import Fieldset from './Fieldset';
import SubmitButton from '../buttons/SubmitButton';
import { FieldState } from '../../../../types/form';

export const Form = (props: any) => {
  const { config, controller, isLast, setIndex, updateFormData } = props;

  const [globalState, setGlobalState] = useState<FieldState[]>(); // global!

  useEffect(() => {
    setGlobalState(controller(config));
  }, [config, controller]);

  const handleChange = (name: string, value: any) => {
    const event = { name, value };
    const newState = controller(config, globalState, event);
    setGlobalState(newState);
  };

  const handleSubmit = (e: any) => {
    e.preventDefault();

    if (!isLast) {
      setIndex((prevCount: number) => prevCount + 1);
    }

    const formData = globalState && reducer(globalState);

    updateFormData(formData);
  };

  console.log(globalState);

  const isList = globalState && globalState.length > 1;

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
                {...props}
                globalState={globalState}
                handleChange={handleChange}
              ></Fieldset>
              {isList && <div className="px-2 bg-gray-400"></div>}
            </Fragment>
          )}
          <SubmitButton isLast={isLast}></SubmitButton>
        </form>
      </div>
    </div>
  );
};

export default Form;
