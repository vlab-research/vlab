import Header from './Header';
import BackButton from './BackButton';
import { StudyConfButton } from '../pages/StudiesPage/components/StudyList';
import { createSlugFor } from '../helpers/strings';
import { useHistory } from 'react-router-dom';

const PageLayout = ({
  title,
  children,
  showBackButton = false,
  testId,
  topRightElements,
}: {
  title: string;
  children: JSX.Element;
  showBackButton?: boolean;
  testId?: string;
  topRightElements?: React.ReactNode;
}) => {
  const history = useHistory();

  const slug = createSlugFor(title);

  const isStudyProgressPage = history.location.pathname === `/studies/${slug}`;

  return (
    <div className="min-h-screen bg-gray-100" data-testid={testId}>
      <Header className="sticky top-0 z-10" />
      <div className="py-10">
        <header>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center">
              {showBackButton && <BackButton />}
              <h1 className="text-3xl font-bold leading-tight text-gray-900 flex-1">
                {title}
              </h1>
              <div>{topRightElements}</div>
              {isStudyProgressPage && (
                <div className="flex flex-row items-center my-2.5">
                  <StudyConfButton slug={slug} testId="study-conf-button" />
                </div>
              )}
            </div>
          </div>
        </header>
        <main>
          <div className="max-w-7xl mx-auto sm:px-6 lg:px-8">
            <div className="px-4 py-5 sm:px-0">{children}</div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default PageLayout;
