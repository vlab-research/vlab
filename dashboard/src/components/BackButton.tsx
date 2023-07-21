import { ArrowLeftIcon } from '@heroicons/react/solid';
import { useHistory } from 'react-router-dom';

const BackButton = () => {
  const history = useHistory();

  const handleBackNavigation = () => {
    return history.push('/studies');
  };

  return (
    <div className="mr-4">
      <button
        className="p-1 rounded-full transition-color text-indigo-600 hover:bg-indigo-100 transition duration-300 ease-in-out focus:outline-none"
        data-testid="back-button"
        tabIndex={0}
        onClick={handleBackNavigation}
      >
        <ArrowLeftIcon className="h-8 w-8" aria-hidden="true" />
      </button>
    </div>
  );
};

export default BackButton;
