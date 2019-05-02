import React from 'react';
import { StartTimeHistogram, DurationHistogram } from '../../components';
import './ResponseScreen.css';

const ResponseScreen = () => {
  return (
    <div style={{ height: '100vh', width: '100vw' }}>
      <StartTimeHistogram formid="form1" />
      <DurationHistogram formid="form1" />
    </div>
  );
};

export default ResponseScreen;
