export type Event = {
  name: string;
  value: any;
};

export const updateLocalState = (state: any[], event: Event) => {
  const clone = [...state];
  const index = clone.findIndex((obj: any) => obj.name === event.name);
  clone[index].value = event.value;
  return clone;
};
