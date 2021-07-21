import Header from './Header';

const PageLayout = ({
  title,
  children,
}: {
  title: string;
  children: JSX.Element;
}) => (
  <div className="min-h-screen bg-gray-100">
    <Header className="sticky top-0 z-10" />
    <div className="py-10">
      <header>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold leading-tight text-gray-900">
            {title}
          </h1>
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
