import { queryCache } from 'react-query';
import { useHistory } from 'react-router-dom';
import StudyList, { StudyListSkeleton } from './components/StudyList';
import useStudies from './hooks/useStudies';
import PageLayout from '../../components/PageLayout';
import PrimaryButton from '../../components/PrimaryButton';
import ErrorPlaceholder from '../../components/ErrorPlaceholder';

const StudiesPage = () => {
  const studies = useStudies();
  const studiesExist = studies.studies.length > 0;

  return (
    <PageLayout
      title={'Studies'}
      testId="studies-page"
      topRightElements={
        studiesExist && (
          <NewStudyButton testId="new-study-button--in-top-right-pagelayout" />
        )
      }
    >
      <PageContent {...studies} />
    </PageLayout>
  );
};

const PageContent = ({
  query,
  queryKey,
  studiesPerPage,
  studies,
  errorMessage,
}: ReturnType<typeof useStudies>) => {
  if (query.isLoading) {
    return <StudyListSkeleton numberItems={studiesPerPage} />;
  }

  if (query.isError) {
    return (
      <ErrorPlaceholder
        onClickTryAgain={() => queryCache.invalidateQueries(queryKey)}
        message={errorMessage}
      />
    );
  }

  if (!studies.length) {
    return <NoStudiesPlaceholder />;
  }

  return (
    <StudyList
      studies={studies}
      studiesPerPage={studiesPerPage}
      isLoadingMoreStudies={query.isFetching}
      canFetchMoreStudies={query.canFetchMore || false}
      onFetchMoreStudies={query.fetchMore}
    />
  );
};

const NoStudiesPlaceholder = () => (
  <div className="shadow overflow-hidden sm:rounded-md">
    <div className="px-4 py-5 bg-white sm:p-6">
      <div className="text-center py-20">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            vectorEffect="non-scaling-stroke"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No studies</h3>
        <p className="mt-1 text-sm text-gray-500">
          Get started by creating a new study.
        </p>
        <div className="mt-6">
          <NewStudyButton testId="new-study-button--in-empty-page" />
        </div>
      </div>
    </div>
  </div>
);

const NewStudyButton = ({ testId }: { testId: string }) => {
  const history = useHistory();

  return (
    <PrimaryButton
      leftIcon="PlusCircleIcon"
      testId={testId}
      onClick={() => history.push('/new-study')}
    >
      New Study
    </PrimaryButton>
  );
};

export default StudiesPage;
