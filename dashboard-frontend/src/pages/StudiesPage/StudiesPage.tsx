import React from 'react';
import { queryCache } from 'react-query';
import useStudies from './useStudies';
import StudyList, { StudyListSkeleton } from './StudyList';
import PageLayout from '../../components/PageLayout';
import PrimaryButton from '../../components/PrimaryButton';
import { ReactComponent as PlaceholderIllustration } from '../../assets/customer-survey-illustration.svg';

const StudiesPage = () => (
  <PageLayout title={'Studies'}>
    <PageContent />
  </PageLayout>
);

const PageContent = () => {
  const { query, queryKey, studiesPerPage, studies, errorMessage } =
    useStudies();

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

const ErrorPlaceholder = ({
  message,
  onClickTryAgain,
}: {
  message: string;
  onClickTryAgain: () => void;
}) => (
  <PlaceholderLayout>
    <Explanation>{message}</Explanation>
    <PrimaryButton className="mt-8" size="500" onClick={onClickTryAgain}>
      Please try again
    </PrimaryButton>
  </PlaceholderLayout>
);

const NoStudiesPlaceholder = () => (
  <PlaceholderLayout>
    <Explanation>
      Contact{' '}
      <a
        href="mailto:info@vlab.digital?subject=[New Account] Create first Study"
        className="text-indigo-600"
      >
        info@vlab.digital
      </a>{' '}
      and create your first Study.
    </Explanation>
  </PlaceholderLayout>
);

const PlaceholderLayout = ({
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

const Explanation = ({ children }: { children: React.ReactNode }) => (
  <p className="pt-4 text-base px-8 sm:pt-6 sm:text-lg lg:pt-8 lg:text-2xl 2xl:pt-8 2xl:text-2xl">
    {children}
  </p>
);

export default StudiesPage;
