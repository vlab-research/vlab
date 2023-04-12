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
  fields: FieldBase[];
}

export type ConfBase = ConfObjectBase | ConfSelectBase | ConfListBase;

export interface FieldBase {
  name: string;
  type: string;
  label: string;
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

export interface Selector {
  name: string;
  type: string;
  label: string;
  options: any[];
}

export interface DataEvent {
  type: string; // can restrict to enum
  value: any;
}

export interface EventInterface extends DataEvent {
  name: string;
  fieldType: string;
}
