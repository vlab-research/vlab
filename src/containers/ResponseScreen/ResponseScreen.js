import React from 'react';
import { StartTimeHistogram, DurationHistogram } from '../../components';
import './ResponseScreen.css';

const ResponseScreen = () => {
  return (
    <div style={{ height: '100vh', width: '100vw' }}>
      <StartTimeHistogram formid="form1" />
      <DurationHistogram />
    </div>
  );
};

export default ResponseScreen;
