const simpleList = {
  type: 'confList',
  title: 'Simple List',
  description: 'simple list conf...',
  key: 'foo',
  input: {
    // input is the only thing that repeats here
    name: 'foo',
    type: 'text',
    label: 'I am a list item',
    helper_text: 'Foo',
  },
  button: {
    name: 'add_button',
    type: 'button',
  },
};

export default simpleList;
