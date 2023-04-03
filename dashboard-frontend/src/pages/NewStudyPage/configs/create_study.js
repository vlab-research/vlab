export const create_study = {
  type: 'confObject',
  title: 'Create a study',
  description: 'Give your new study a name.',
  fields: [
    {
      name: 'name',
      type: 'text',
      label: 'Give your study a name',
      helper_text: 'E.g example-fly-conf',
    },
  ],
};
