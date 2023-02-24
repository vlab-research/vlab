import { Field, FieldState } from '../../../../types/form';

const Fieldset = (props: any) => {
  const { globalState, handleChange } = props;

  const mapStateToFields = (state: FieldState[]) => {
    const newState: any[] = [];

    state.forEach(stateObj => {
      if (stateObj.component) {
        const { component, ...props } = stateObj;

        newState.push({
          ...props,
          Component: component,
        });
      }
    });

    return newState;
  };

  const renderFields = (fields: Field[]) => {
    return fields.map(field => {
      const { Component, ...props } = field;
      const { name } = props;

      const callback = (e: any) => {
        handleChange(name, e.target.value);
      };

      return <Component key={name} onChange={callback} {...props} />;
    });
  };

  const fields = mapStateToFields(globalState);

  return globalState && renderFields(fields);
};

export default Fieldset;
