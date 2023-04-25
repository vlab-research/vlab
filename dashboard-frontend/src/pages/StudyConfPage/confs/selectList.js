const selectList = {
  type: 'confList',
  title: 'Select List',
  description: 'select list conf...',
  key: 'fizz',
  input: {
    // input is the only thing that repeats here
    name: 'foo',
    type: 'select',
    label: 'I am a simple select field',
    options: [
      {
        name: 'foobar',
        label: 'Foobar',
      },
      {
        name: 'foobaz',
        label: 'Foobaz',
      },
      {
        name: 'foobazzle',
        label: 'Foobazzle',
      },
    ],
  },
  button: {
    name: 'add_button',
    type: 'button',
  },
};

export default selectList;
