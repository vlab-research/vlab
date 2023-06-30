import { TrashIcon } from '@heroicons/react/solid';

type Props = {
  onClick?: () => void;
};

const DeleteButton = ({ onClick }: Props) => {
  return (
    <button onClick={onClick} className="flex focus:outline-none" type="button">
      <span className="flex items-center justify-center">
        <TrashIcon
          className="h-8 w-8 text-gray-500 hover:text-gray-600 transition duration-300 ease-in-out"
          aria-hidden="true"
        />
      </span>
    </button>
  );
};

export default DeleteButton;
