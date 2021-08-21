import React from 'react';
import { queryCache } from 'react-query';
import useStudies from './useStudies';
import StudyList, { StudyListSkeleton } from './StudyList';
import PageLayout from '../../components/PageLayout';
import ErrorPlaceholder, {
  PlaceholderLayout,
  Explanation,
} from '../../components/ErrorPlaceholder';

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

export default StudiesPage;
