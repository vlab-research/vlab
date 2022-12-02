export const creative = {
  type: 'config-object',
  title: 'Creative',
  description: 'Recruitment needs ads and ads need creative.',
  fields: [
    {
      name: 'destination',
      type: 'text',
      label: 'Destination',
      helperText: 'E.g fly',
    },
    {
      name: 'name',
      type: 'text',
      label: 'Name',
      helperText: 'E.g vlab-vaping-pilot-banner-99',
    },
    {
      name: 'image_hash',
      type: 'text',
      label: 'Image hash',
      helperText: 'E.g lk2j34',
    },
    {
      name: 'body',
      type: 'text',
      label: 'Body',
      helperText: 'E.g Take this 15-minute survey and win a gift card!',
    },
    {
      name: 'link_text',
      type: 'text',
      label: 'Link text',
      helperText: 'E.g Take the survey now!',
    },
    {
      name: 'welcome_message',
      type: 'text',
      label: 'Welcome message',
      helperText:
        "E.g Welcome! We're running a small survey and are looking for participants. You can win an Amazon gift card if you partcipate!",
    },
    {
      name: 'button_text',
      type: 'text',
      label: 'Button text',
      helperText: 'E.g Continue',
    },
  ],
};
