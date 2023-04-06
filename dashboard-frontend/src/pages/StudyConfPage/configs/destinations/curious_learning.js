export const curious_learning = {
  type: 'confObject',
  title: 'Curious Learning',
  description: 'Curious Learning...',
  key: 'from',
  fields: [
    {
      name: 'from',
      type: 'number',
      label: 'From',
      helper_text: 'E.g 17/12/22',
    },
    {
      name: 'app_id',
      type: 'text',
      label: 'App id',
      helper_text: 'E.g 12345',
    },
    {
      name: 'facebook_app_id',
      type: 'text',
      label: 'Facebook App id',
      helper_text: 'E.g 12345',
    },
    {
      name: 'user_device',
      type: 'list',
      label: 'Saved user devices',
      options: [
        {
          name: 'user_device_1',
          label: 'User Device 1',
        },
        {
          name: 'user_device_2',
          label: 'User Device 2',
        },
        {
          name: 'user_device_3',
          label: 'User Device 3',
        },
      ],
    },
  ],
};

export default curious_learning;
