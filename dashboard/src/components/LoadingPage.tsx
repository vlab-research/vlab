import { ReactComponent as Logo } from '../assets/logo.svg';
const LoadingPage = ({ text }: { text?: string; }) => (
  <div
    className="h-96 flex justify-center"
    data-testid="loading-page"
  >
    <div className="self-center">
      <Logo
        className="h-12 animate-pulse"
        title="Virtual Lab logo"
      />

      {text &&
        <h2 className="flex justify-center text-l my-6 text-500">
          {text}
        </h2>
      }
    </div>
  </div>
);

export default LoadingPage
