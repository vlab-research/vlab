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
  // The "(not yet enabled)" label was wrong and worse than wrong: adopt did not
  // refuse a multi destination, it silently loaded one as a Messenger
  // destination. `DestinationConf` was an undiscriminated union whose first
  // member accepted any `type`, so `multi` never once produced a
  // FlyMultiDestination. Fixed 2026-08-30 by discriminating the union; the
  // WhatsApp arm is now reachable but still unverified against real delivery,
  // which is what the label says.
  {
    name: 'multi',
    label: 'Messenger + WhatsApp (WhatsApp arm unverified)',
  },
];

export default destinations;
