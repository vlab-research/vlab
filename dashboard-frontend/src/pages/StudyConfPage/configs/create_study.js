export const create_study = {
  type: 'configObject',
  title: 'Create a study',
  description: 'This is where you give your new study a name.',
  fields: [
    {
      name: 'name',
      type: 'text',
      label: 'Give your study a name',
      helper_text: 'E.g example-fly-conf',
    },
  ],
};
