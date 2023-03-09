import { useState } from 'react';
import { PlusCircleIcon } from '@heroicons/react/solid';

const Button = (props: any) => {
  const { label, onChange } = props;

  const handleClick = (e: any) => onChange(e);

  return (
    <div className="flex justify-center p-2 sm:my-4">
      <button
        type="button"
        className="flex flex-row items-center"
        onClick={handleClick}
      >
        <PlusCircleIcon
          className="mr-1.5 h-5 w-5 text-gray-400"
          aria-hidden="true"
        ></PlusCircleIcon>
        <span className="block text-sm font-medium text-gray-700">{label}</span>
      </button>
    </div>
  );
};

export default Button;
