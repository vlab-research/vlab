export interface ConfBase extends Record<string, any> {
  title: string;
  type: string;
  description: string;
  fields: FieldBase[];
}

export interface FieldBase {
  name: string;
  type: string;
  label: string;
  helper_text?: string;
  options?: any[];
}

export interface FieldState extends FieldBase {
  id: string;
  component: any;
  value: any;
}

export interface Field extends FieldState {
  Component: React.FunctionComponent<any>;
}
