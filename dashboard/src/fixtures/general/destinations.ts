const destinations = [
  {
    name: '',
    label: 'Select a destination',
  },
  {
    name: 'messenger',
    label: 'Messenger',
  },
  {
    name: 'website',
    label: 'Web',
  },
  {
    name: 'app',
    label: 'App',
  },
  {
    name: 'whatsapp',
    label: 'WhatsApp',
  },
  // Labelled as not-yet-enabled because it is: adopt refuses to load a multi
  // destination until the WhatsApp arm has been measured against real Meta
  // delivery. Left selectable rather than hidden so the capability is
  // discoverable and the save error explains itself, instead of the option
  // silently not existing.
  {
    name: 'multi',
    label: 'Messenger + WhatsApp (not yet enabled)',
  },
];

export default destinations;
