import React from 'react';

interface Props {
  children: React.ReactNode;
}
const ConfWrapper: React.FC<Props> = ({ children }) => {

  return (
    <div className="md:grid md:grid-cols-12 md:gap-4">
      <div className="md:col-span-3">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-9">
        <div className="px-4 py-3 bg-gray-50 sm:px-6">
          <div className="sm:my-4">
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ConfWrapper
