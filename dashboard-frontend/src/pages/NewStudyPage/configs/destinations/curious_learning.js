export const curious_learning = {
  type: 'config-object',
  title: 'Curious Learning',
  description: 'Curious Learning...',
  key: 'form_id', // tells us which field can be used as a unique key
  fields: [
    {
      name: 'from',
      type: 'number',
      label: 'From',
      helpertext: 'E.g 17/12/22',
    },
    {
      name: 'app_id',
      type: 'text',
      label: 'App id',
      helpertext: 'E.g 12345',
    },
    {
      name: 'facebook_app_id',
      type: 'text',
      label: 'Facebook App id',
      helpertext: 'E.g 12345',
    },
    {
      name: 'user_device',
      type: 'list',
      label: 'Add a user device',
      options: [],
    },
  ],
};
