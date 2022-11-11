export const typeform = {
  type: 'config-object',
  title: 'Typeform',
  description: 'Typeform...',
  key: 'form_id', // tells us which field can be used as a unique key
  fields: [
    {
      form_id: {
        name: 'form_id',
        type: 'text',
        label: 'Form id',
        helpertext: 'E.g 12345',
      },
    },
  ],
};
