import { classNames } from '../helpers/strings';

const ConnectButton = ({
  buttonLabel,
  slug,
}: {
  buttonLabel: String;
  slug: String;
}) => {
  return (
    <>
      <button
        className={classNames(
          'my-2 sm:self-center items-center px-4 py-2 col-span-1 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50'
        )}
        data-testid={`connect-button-${buttonLabel}`}
      ></button>
    </>
  );
};

export default ConnectButton;
