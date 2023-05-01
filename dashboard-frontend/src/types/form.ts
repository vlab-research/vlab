export type ConfBase = ConfObjectBase | ConfSelectBase;

export interface ConfObjectBase extends Record<string, any> {
  title: string;
  type: string;
  description: string;
  fields: FieldBase[];
  Component?: React.FunctionComponent<any>;
}

export interface ConfSelectBase extends Record<string, any> {
  title: string;
  type: string;
  description: string;
  selector: any;
  Component: React.FunctionComponent<any>;
}

export interface TranslatedConf extends Record<string, any> {
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
