const app = {
  type: 'confObject',
  title: 'App',
  description: 'App...',
  key: 'name',
  fields: [
    {
      name: 'facebook_app_id',
      type: 'text',
      label: 'Facebook app id',
      helper_text: 'E.g',
    },
    {
      name: 'app_install_link',
      type: 'text',
      label: 'App install link',
      helper_text: 'E.g',
    },
    {
      name: 'deeplink_template',
      type: 'text',
      label: 'Deeplink template',
      helper_text: 'E.g',
    },
    {
      name: 'app_install_state',
      type: 'text',
      label: 'App install state',
      helper_text: 'E.g',
    },
    {
      name: 'user_device',
      type: 'list',
      label: 'User devices',
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
    {
      name: 'user_os',
      type: 'list',
      label: 'User OS',
      options: [
        {
          name: 'user_os_1',
          label: 'User Device 1',
        },
        {
          name: 'user_os_2',
          label: 'User Device 2',
        },
        {
          name: 'user_os_3',
          label: 'User Device 3',
        },
      ],
    },
  ],
};

export default app;
