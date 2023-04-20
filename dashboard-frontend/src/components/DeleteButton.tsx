import { TrashIcon } from '@heroicons/react/solid';
import LoadingSpinner from './LoadingSpinner';

type props = {
  onClick?: (e: any) => void;
  type?: 'button' | 'submit';
  loading?: boolean;
};

const DeleteButton: React.FC<props> = ({ onClick, type, loading }) => {
  return (
    <button
      onClick={onClick}
      type={type}
      name="delete"
      disabled={loading}
      className="flex px-5 py-5 border border-transparent text-base font-medium rounded-md shadow-sm bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-md ml-3 mr-3 h-5 w-5 content-evenly"
    >
      <span className="absolute">
        <TrashIcon className="-ml-2.5 -my-2.5 mr-5 h-5 w-5" />
      </span>
      {loading && (
        <span className="absolute">
          <LoadingSpinner />
        </span>
      )}
    </button>
  );
};

export default DeleteButton;
