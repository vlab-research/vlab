export interface Config extends Record<string, any> {
  title: string;
  type: string;
  description: string;
  fields?: FieldBase[];
  selector?: Selector;
}

export interface FieldBase {
  name: string;
  type: string;
  label: string;
  helper_text?: string;
  options?: any[];
  call_to_action?: string;
}
export interface Selector {
  name: string;
  type: string;
  label: string;
  options: Config[];
}

export interface FieldState extends FieldBase {
  id: string;
  component: any;
  value: any;
}

export interface Field extends FieldState {
  Component: React.FunctionComponent<any>;
}
