export interface ConfigBase extends Record<string, any> {
  title: string;
  description: string;
  fields?: FieldBase[];
  selector?: {
    name: string;
    type: string;
    label: string;
    options: ConfigBase[];
  };
}

export interface FieldBase {
  name: string;
  type: string;
  label: string;
  helper_text?: string;
  defaultValue?: string;
  options?: {
    name: string;
    label: string;
  }[];
  call_to_action?: string;
}

export interface FieldState extends FieldBase {
  id: string;
  component: any;
  value: string | number;
}

export interface Field extends FieldState {
  Component: React.FunctionComponent<any>;
}
