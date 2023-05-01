import React from 'react';

const General: React.FC = ({ ...conf }: any) => {
  console.log(conf);
  return <div className="sm:my-4">general conf</div>;
};

export default General;
