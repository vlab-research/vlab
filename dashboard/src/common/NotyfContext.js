import React from 'react';
import { Notyf } from 'notyf';

// set your global Notyf configuration here
export default React.createContext(
  new Notyf({
    duration: 1000,
    position: {
      x: 'bottom',
      y: 'right',
    },
    types: [
      {
        type: 'warning',
        background: 'rgb(156 163 175)',
        icon: {
          className: 'material-icons',
          text: 'warning',
        },
      },
      {
        type: 'error',
        background: 'rgb(251 113 133)',
        dismissible: true,
      },
      {
        type: 'info',
        background: 'rgb(67 56 202)',
        icon: {
          className: 'material-icons',
        },
      },
    ],
  })
);
