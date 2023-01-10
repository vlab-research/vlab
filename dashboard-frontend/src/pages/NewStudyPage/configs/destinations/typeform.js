export const typeform = {
  type: 'configObject',
  title: 'Typeform',
  description: 'Typeform...',
  key: 'form_id', // tells us which field can be used as a unique key
  fields: [
    {
      name: 'form_id',
      type: 'text',
      label: 'Form id',
      helper_text: 'E.g 12345',
    },
  ],
};
