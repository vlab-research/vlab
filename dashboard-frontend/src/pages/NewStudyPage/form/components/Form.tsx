import { Fragment, useEffect, useState } from 'react';
import { createInitialState } from '../../../../helpers/createInitialState';
import { reducer } from '../../../../helpers/objects';
import Fieldset from './Fieldset';
import SubmitButton from '../buttons/SubmitButton';

export const FormNew = (props: any) => {
  const { config, controller, isLast, setIndex, updateFormData } = props;

  const [state, setState] = useState<any[]>(); // global!

  useEffect(() => {
    setState(createInitialState(config));
  }, [config]);

  const handleChange = (name: string, value: any) => {
    const event = { name, value };
    const newState = controller(config, state, event);
    setState(newState);
  };

  const handleSubmit = (e: any) => {
    e.preventDefault();

    if (!isLast) {
      setIndex((prevCount: number) => prevCount + 1);
    }

    const formData = state && reducer(state);

    updateFormData(formData);
  };

  const isList = state && state.length > 1;

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <form onSubmit={handleSubmit}>
          {state && (
            <Fragment>
              <Fieldset
                {...props}
                state={state}
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

export default FormNew;
