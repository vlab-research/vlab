export interface ConfObjectBase extends Record<string, any> {
  title: string;
  type: string;
  description: string;
  fields: FieldBase[];
}

export interface ConfSelectBase extends Record<string, any> {
  title: string;
  type: string;
  description: string;
  selector: Selector;
}

export interface ConfListBase extends Record<string, any> {
  title: string;
  type: string;
  description: string;
  input: FieldBase;
  button: Button;
}

export interface Selector {
  name: string;
  type: string;
  label: string;
  options: any[];
}

export interface Button {
  name: string;
  type: string;
}

export interface FieldBase {
  name: string;
  type: string;
  label?: string;
  helper_text?: string;
  options?: any[];
  conf?: any;
}

export interface FieldState extends FieldBase {
  id: string;
  component: any;
  value: any;
}

export interface Field extends FieldState {
  Component: React.FunctionComponent<any>;
}

export type ConfBase = ConfObjectBase | ConfSelectBase | ConfListBase;
