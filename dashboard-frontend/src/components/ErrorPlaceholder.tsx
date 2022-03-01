import PrimaryButton from './PrimaryButton';
import { ReactComponent as PlaceholderIllustration } from '../assets/customer-survey-illustration.svg';

const ErrorPlaceholder = ({
  message,
  onClickTryAgain,
}: {
  message: string;
  onClickTryAgain: () => void;
}) => (
  <PlaceholderLayout>
    <Explanation>{message}</Explanation>
    <PrimaryButton
      rounded
      className="mt-8"
      size="500"
      onClick={onClickTryAgain}
    >
      Please try again
    </PrimaryButton>
  </PlaceholderLayout>
);

export const PlaceholderLayout = ({
  children,
}: {
  children: JSX.Element | JSX.Element[];
}) => (
  <div className="bg-white shadow overflow-hidden rounded-none py-8 sm:rounded-md sm:py-20 lg:py-8 2xl:py-28">
    <div className="flex flex-col justify-center items-center">
      <PlaceholderIllustration
        className="h-28 sm:h-40 lg:h-64 2xl:h-80"
        title="Placeholder image"
      />
      {children}
    </div>
  </div>
);

export const Explanation = ({ children }: { children: React.ReactNode }) => (
  <p className="pt-4 text-base px-8 sm:pt-6 sm:text-lg lg:pt-8 lg:text-2xl 2xl:pt-8 2xl:text-2xl">
    {children}
  </p>
);

export default ErrorPlaceholder;
