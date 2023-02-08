export const creative = {
  type: 'configObject',
  title: 'Creative',
  description: 'Recruitment needs ads and ads need creative.',
  fields: [
    {
      name: 'destination_name',
      type: 'text',
      label: 'Destination name',
      helper_text: 'E.g fly',
    },
    {
      name: 'name',
      type: 'text',
      label: 'Name',
      helper_text: 'E.g vlab-vaping-pilot-banner-99',
    },
    {
      name: 'image_hash',
      type: 'text',
      label: 'Image hash',
      helper_text: 'E.g lk2j34',
    },
    {
      name: 'body',
      type: 'text',
      label: 'Body',
      helper_text: 'E.g Take this 15-minute survey and win a gift card!',
    },
    {
      name: 'link_text',
      type: 'text',
      label: 'Link text',
      helper_text: 'E.g Take the survey now!',
    },
    {
      name: 'welcome_message',
      type: 'text',
      label: 'Welcome message',
      helper_text:
        "E.g Welcome! We're running a small survey and are looking for participants. You can win an Amazon gift card if you partcipate!",
    },
    {
      name: 'button_text',
      type: 'text',
      label: 'Button text',
      helper_text: 'E.g Continue',
    },
  ],
};
