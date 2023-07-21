import { PlusCircleIcon } from '@heroicons/react/solid';

type Props = {
  onClick?: () => void;
  label?: string;
};

const AddButton = ({ onClick, label }: Props) => {
  return (
    <div className="flex flex-row items-center mt-2">
      <button
        onClick={onClick}
        className="flex items-center focus:outline-none"
        type="button"
      >
        <PlusCircleIcon
          className="h-8 w-8 text-gray-500 hover:text-gray-600 transition duration-300 ease-in-out focus:outline-none"
          aria-hidden="true"
        />
        <span className="ml-2 italic text-gray-700 text-sm cursor-pointer">
          {label}
        </span>
      </button>
    </div>
  );
};

export default AddButton;
