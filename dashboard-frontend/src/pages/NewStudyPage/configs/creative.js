export const creative = {
  configType: 'creative',
  description: 'Recruitment needs ads and ads need creative.',
  fields: [
    {
      name: 'destination',
      type: 'text',
      label: 'Destination',
      helpertext: 'E.g fly',
    },
    {
      name: 'name',
      type: 'text',
      label: 'Name',
      helpertext: 'E.g vlab-vaping-pilot-banner-99',
    },
    {
      name: 'image_hash',
      type: 'text',
      label: 'Image hash',
      helpertext: 'E.g lk2j34',
    },
    {
      name: 'body',
      type: 'text',
      label: 'Body',
      helpertext: 'E.g Take this 15-minute survey and win a gift card!',
    },
    {
      name: 'link_text',
      type: 'text',
      label: 'Link text',
      helpertext: 'E.g Take the survey now!',
    },
    {
      name: 'welcome_message',
      type: 'text',
      label: 'Welcome message',
      helpertext:
        "E.g Welcome! We're running a small survey and are looking for participants. You can win an Amazon gift card if you partcipate!",
    },
    {
      name: 'button_text',
      type: 'text',
      label: 'Button text',
      helpertext: 'E.g Continue',
    },
  ],
};
