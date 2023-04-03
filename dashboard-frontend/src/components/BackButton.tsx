import { ArrowLeftIcon } from '@heroicons/react/solid';
import { useHistory } from 'react-router-dom';

const BackButton = () => {
  const history = useHistory();

  const handleBackNavigation = () => {
    const currentRouteIsLastOne = history.location.key === undefined;

    if (currentRouteIsLastOne) {
      return history.push('/studies');
    }

    return history.goBack();
  };

  return (
    <div className="mr-4 cursor-pointer outline-none">
      <div
        className="p-1 rounded-full transition-color text-indigo-600 hover:bg-indigo-100"
        data-testid="back-button"
        role="button"
        tabIndex={0}
        onClick={handleBackNavigation}
      >
        <ArrowLeftIcon className="h-8 w-8" aria-hidden="true" />
      </div>
    </div>
  );
};

export default BackButton;
