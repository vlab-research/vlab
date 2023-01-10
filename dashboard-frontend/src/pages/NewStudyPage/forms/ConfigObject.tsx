import { Form } from '../Form';

const ConfigObject = (props: any) => {
  const { config } = props;
  const { fields } = config;

  return <Form fields={fields} {...props}></Form>;
};

export default ConfigObject;
