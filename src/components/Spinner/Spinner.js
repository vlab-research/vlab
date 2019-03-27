import React from 'react';
import spinner from './spinner.svg';

const Spinner = () => {
  const style = {
    position: 'absolute',
    display: 'flex',
    justifyContent: 'center',
    height: '100vh',
    width: '100vw',
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'white',
  };

  return (
    <div style={style}>
      <img src={spinner} alt="loading" />
    </div>
  );
};

export default Spinner;
