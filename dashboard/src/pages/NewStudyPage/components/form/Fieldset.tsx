import { Field, FieldState } from '../../../../types/form';

const Fieldset = (props: any) => {
  const { fields, handleChange, error_message } = props;

  const mapComponentToFields = (fields: FieldState[]) => {
    const newState: any[] = [];

    fields.forEach(field => {
      if (field.component) {
        const { component, ...props } = field;

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
      const { name, type } = props;

      const callback = (e: any) => {
        handleChange(name, type, e);
      };

      return (
        <Component
          key={name}
          onChange={callback}
          error_message={error_message}
          {...props}
        />
      );
    });
  };

  const f = mapComponentToFields(fields);

  return fields && renderFields(f);
};

export default Fieldset;
