import Header from './Header';
import BackButton from './BackButton';

const PageLayout = ({
  title,
  children,
  showBackButton = false,
  testId,
}: {
  title: string;
  children: JSX.Element;
  showBackButton?: boolean;
  testId?: string;
}) => (
  <div className="min-h-screen bg-gray-100" data-testid={testId}>
    <Header className="sticky top-0 z-10" />
    <div className="py-10">
      <header>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-start">
            {showBackButton && <BackButton />}
            <h1 className="text-3xl font-bold leading-tight text-gray-900">
              {title}
            </h1>
          </div>
        </div>
      </header>
      <main>
        <div className="max-w-7xl mx-auto sm:px-6 lg:px-8">
          <div className="px-4 py-8 sm:px-0">{children}</div>
        </div>
      </main>
    </div>
  </div>
);

export default PageLayout;
