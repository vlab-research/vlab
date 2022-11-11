export const curious_learning = {
  type: 'config-object',
  title: 'Curious Learning',
  description: 'Curious Learning...',
  key: 'form_id', // tells us which field can be used as a unique key
  fields: [
    {
      from: {
        name: 'from',
        type: 'number',
        label: 'From',
        helpertext: 'E.g 17/12/22',
      },
    },
    {
      app_id: {
        name: 'app_id',
        type: 'text',
        label: 'App id',
        helpertext: 'E.g 12345',
      },
    },
    {
      facebook_app_id: {
        name: 'facebook_app_id',
        type: 'text',
        label: 'Facebook App id',
        helpertext: 'E.g 12345',
      },
    },
    {
      user_device: {
        name: 'user_device',
        type: 'list',
        label: 'Add a user device',
        options: [],
      },
    },
  ],
};
