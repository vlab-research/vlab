const simpleList = {
  type: 'confList',
  title: 'Test',
  description: 'test...',
  key: 'foo',
  fields: [
    {
      name: 'foo',
      type: 'text',
      label: 'Foo',
      helper_text: 'Foo',
    },
    {
      name: 'bar',
      type: 'text',
      label: 'Bar',
      helper_text: 'Bar',
    },
    {
      name: 'baz',
      type: 'text',
      label: 'Baz',
      helper_text: 'Baz',
    },
    {
      name: 'add_button',
      type: 'button',
      label: 'Add',
    },
  ],
};

export default simpleList;
