export const destination = {
  type: 'confList',
  title: 'Destination',
  description: 'Blah Blah',
  fields: [
    {
      type: 'fieldset',
      name: f => `${f.value.name}`,
      label: f => `${f.value.name}`,
      conf: { // this is essentially a recruitment.js, it's a confSelect
        type: 'confSelect',
        title: 'Someting',
        description:
          'something something',
        selector: {
          name: 'destination_type',
          type: 'select',
          label: 'Select a destination type',
          options: [{}, {}, {}], // destination
        },
      },
    },
    {
      type: 'button',
      label: 'Add a destination',
      name: 'addDestination'
    },
  ]
};
