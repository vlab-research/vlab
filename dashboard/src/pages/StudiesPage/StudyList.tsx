import React, { useCallback } from 'react';
import { CalendarIcon } from '@heroicons/react/solid';
import { Link, useHistory } from 'react-router-dom';
import { formatTimestamp } from '../../helpers/dates';
import { StudyResource } from '../../types/study';
import useInfiniteScrolling from './useInfiniteScrolling';
import SecondaryButton from '../../components/SecondaryButton';

const StudyList = ({
  studies,
  studiesPerPage,
  isLoadingMoreStudies,
  canFetchMoreStudies,
  onFetchMoreStudies,
}: {
  studies: StudyResource[];
  studiesPerPage: number;
  isLoadingMoreStudies: boolean;
  canFetchMoreStudies: boolean;
  onFetchMoreStudies: () => void;
}) => {
  const { lastElementRef } = useInfiniteScrolling({
    isLoading: isLoadingMoreStudies,
    canFetchMore: canFetchMoreStudies,
    fetchMore: onFetchMoreStudies,
  });

  return (
    <ListLayout>
      {studies.map((study, index) => (
        <StudyListItem
          key={`${study.id}-${index}`}
          study={study}
          elementRef={studies.length === index + 1 ? lastElementRef : undefined}
        />
      ))}
      {isLoadingMoreStudies && (
        <StudyListSkeletonItems number={studiesPerPage} />
      )}
    </ListLayout>
  );
};

const StudyListItem = ({
  study,
  elementRef,
}: {
  study: StudyResource;
  elementRef?: ReturnType<typeof useCallback>;
}) => (
  <li data-testid="study-list-item" ref={elementRef}>
    <div className="flex flex-row justify-between px-4 py-4 block hover:bg-gray-50 sm:px-6">
      <Link to={`/studies/${study.slug}`} className="w-full block">
        <div className="flex items-center">
          <p className="text-sm font-medium text-indigo-600 truncate">
            {study.name}
          </p>
        </div>
        <div className="mt-2">
          <div className="flex items-center text-sm text-gray-500">
            <CalendarIcon
              className="mr-1.5 h-5 w-5 text-gray-400"
              aria-hidden="true"
            />
            <CreatedDate timestamp={study.createdAt} />
          </div>
        </div>
      </Link>
      <div className="flex flex-row items-center my-2.5">
        <StudyConfButton slug={study.slug} testId="study-conf-button" />
      </div>
    </div>
  </li>
);

const CreatedDate = ({ timestamp }: { timestamp: number }) => {
  const formattedDate = formatTimestamp(timestamp);
  const label =
    formattedDate === 'Today' || formattedDate === 'Yesterday'
      ? 'Created '
      : 'Created on ';

  return (
    <p>
      {label}
      {formattedDate}
    </p>
  );
};

export const StudyListSkeleton = ({ numberItems }: { numberItems: number }) => (
  <ListLayout>
    <StudyListSkeletonItems number={numberItems} />
  </ListLayout>
);

const StudyListSkeletonItems = ({ number }: { number: number }) => (
  <React.Fragment>
    {Array.from({ length: number }, (_, index) => (
      <li
        className="px-4 py-4 sm:px-6"
        data-testid="study-list-skeleton-item"
        key={index}
      >
        <div
          className="animate-pulse"
          style={{
            animationFillMode: 'backwards',
            animationDelay: `${150 * index}ms`,
          }}
        >
          <div className="h-5 bg-gray-200 rounded w-2/5"></div>
          <div className="mt-2 h-5 bg-gray-200 rounded w-1/5"></div>
        </div>
      </li>
    ))}
  </React.Fragment>
);

const ListLayout = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-white shadow overflow-hidden sm:rounded-md">
    <ul className="divide-y divide-gray-200" data-testid="studies-list">
      {children}
    </ul>
  </div>
);

const StudyConfButton = ({
  testId,
  slug,
}: {
  testId: string;
  slug: string;
}) => {
  const history = useHistory();

  return (
    <SecondaryButton
      testId={testId}
      icon="CogIcon"
      onClick={() => history.push(`/studies/${slug}/conf`)}
    >
      {''}
    </SecondaryButton>
  );
};

export default StudyList;
