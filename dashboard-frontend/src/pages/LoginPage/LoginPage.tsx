import useAuth0 from '../../hooks/useAuth0';
import PrimaryButton from '../../components/PrimaryButton';
import { ReactComponent as Logo } from '../../assets/logo.svg';
import { ReactComponent as WelcomeIllustration } from '../../assets/launching-illustration.svg';

const LoginPage = ({
  withGenericError = false,
}: {
  withGenericError?: boolean;
}) => {
  const { loginWithRedirect } = useAuth0();

  return (
    <div className="h-screen flex bg-gray-100 justify-center pt-12">
      <div>
        <div className="flex justify-center pb-8">
          <Logo className="h-12 self-center" title="Virtual Lab logo" />
        </div>

        <div className="bg-white shadow overflow-hidden rounded-none sm:rounded-md pt-8 pb-10">
          <div className="flex flex-col items-center">
            <WelcomeIllustration className="h-56 w-72" />

            <p className="pt-10 pl-9 pr-9 sm:pl-20 sm:pr-20 text-4xl text-gray-900 text-center">
              {withGenericError
                ? 'Oops, something went wrong!'
                : 'Ready to start?'}
            </p>

            <p className="pt-5 pl-9 pr-9 sm:pl-20 sm:pr-20 text-xl text-gray-900 text-center">
              {withGenericError
                ? 'Please check your internet connection and try again.'
                : 'Log in now to view the progress of your Studies!'}
            </p>

            <PrimaryButton
              size="500"
              rounded
              onClick={loginWithRedirect}
              className="mt-8 pl-32 pr-32 sm:pl-44 sm:pr-44"
            >
              Log in
            </PrimaryButton>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
