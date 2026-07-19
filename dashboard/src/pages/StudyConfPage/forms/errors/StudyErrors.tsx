import React from 'react';
import { useParams } from 'react-router-dom';
import ConfWrapper from '../../components/ConfWrapper';
import LoadingPage from '../../../../components/LoadingPage';
import ErrorPlaceholder from '../../../../components/ErrorPlaceholder';
import useStudyErrors from '../../hooks/useStudyErrors';
import { formatRelativeTime, formatTimestamp } from '../../../../helpers/dates';
import { StudyError } from '../../../../types/study';

const severityRank = (severity: string) => (severity === 'error' ? 0 : 1);

const bySeverityThenRecency = (a: StudyError, b: StudyError) =>
  severityRank(a.severity) - severityRank(b.severity) ||
  b.last_seen.localeCompare(a.last_seen);

const groupBySource = (errors: StudyError[]) => {
  const groups: Record<string, StudyError[]> = {};
  for (const e of errors) {
    groups[e.source] = [...(groups[e.source] || []), e];
  }
  return Object.entries(groups).map(([source, errs]) => [
    source,
    errs.sort(bySeverityThenRecency),
  ]) as [string, StudyError[]][];
};

const SeverityIcon: React.FC<{ severity: string }> = ({ severity }) => (
  <span
    title={severity}
    className={`mt-1 flex-none inline-block h-2.5 w-2.5 rounded-full ${
      severity === 'error' ? 'bg-red-500' : 'bg-amber-400'
    }`}
  />
);

const ErrorRow: React.FC<{ error: StudyError }> = ({ error }) => {
  const count = error.details?.count;

  return (
    <li className="flex items-start space-x-3 py-3">
      <SeverityIcon severity={error.severity} />
      <div className="flex-1">
        <p className="text-sm text-gray-900">{error.message}</p>
        <p className="mt-1 text-xs text-gray-500">
          {error.details?.entity && <span className="mr-3">{error.details.entity}</span>}
          {typeof count === 'number' && count > 1 && (
            <span className="mr-3">{count} occurrences</span>
          )}
          <span className="mr-3">since {formatRelativeTime(error.first_seen)}</span>
          <span>last seen {formatRelativeTime(error.last_seen)}</span>
        </p>
      </div>
    </li>
  );
};

const StudyErrors: React.FC = () => {
  const { studySlug } = useParams<{ studySlug: string }>();
  const { errors, isLoading, isError, refetch, lastChecked } =
    useStudyErrors(studySlug);

  if (isLoading) {
    return <LoadingPage text="Checking study health..." />;
  }

  if (isError) {
    return (
      <ErrorPlaceholder
        message="Failed to load study errors"
        onClickTryAgain={refetch}
      />
    );
  }

  // Empty state matters: a visible "healthy, last checked X" is the assurance
  // this surface exists to provide — the motivating incident was silence.
  if (errors.length === 0) {
    return (
      <ConfWrapper>
        <div className="px-4 sm:px-6 lg:px-8">
          <h1 className="text-xl font-semibold text-gray-900">Errors</h1>
          <div className="mt-8 flex items-center space-x-3 text-sm text-gray-600">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-green-500" />
            <span>
              No issues detected.
              {lastChecked &&
                ` Last checked ${formatTimestamp(lastChecked.getTime())}, ${lastChecked.toLocaleTimeString()}.`}
            </span>
          </div>
        </div>
      </ConfWrapper>
    );
  }

  return (
    <ConfWrapper>
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="sm:flex sm:items-center">
          <div className="sm:flex-auto">
            <h1 className="text-xl font-semibold text-gray-900">Errors</h1>
            <p className="mt-2 text-sm text-gray-700">
              Current issues detected across this study's subsystems. Issues
              clear automatically once the underlying system runs healthy again.
            </p>
          </div>
        </div>
        {groupBySource(errors).map(([source, errs]) => (
          <div key={source} className="mt-8">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
              {source}
            </h2>
            <ul className="mt-2 divide-y divide-gray-200 border-t border-b border-gray-200">
              {errs.map(e => (
                <ErrorRow key={e.fingerprint} error={e} />
              ))}
            </ul>
          </div>
        ))}
      </div>
    </ConfWrapper>
  );
};

export default StudyErrors;
