import React from 'react';
import { useParams } from 'react-router-dom';
import ConfWrapper from '../../components/ConfWrapper';
import LoadingPage from '../../../../components/LoadingPage';
import ErrorPlaceholder from '../../../../components/ErrorPlaceholder';
import useAdAttributions from '../../hooks/useAdAttributions';

/**
 * What each of this study's ads means, and the code it carries.
 *
 * This is a confirmation surface, not a configuration one. A researcher does
 * not choose the ref codes their ads carry — vlab mints them, deterministically,
 * from the stratum and creative — so the honest answer to "where do I see the
 * ref codes" is: here, after the ads are built.
 *
 * It matters because the failure this whole mechanism guards against is a
 * quiet one. A study whose write side and read side do not line up produces no
 * error a researcher would see; it produces strata that count zero and an
 * optimizer reallocating budget away from a stratum that is recruiting
 * perfectly well. Seeing the rows turns "hope the two halves line up" into
 * "see that they do".
 *
 * Rows are frozen at ad creation and never refreshed, and every row is shown
 * including ads Facebook no longer has — respondents keep arriving from deleted
 * ads through reshared page posts, so hiding those rows would make attributed
 * respondents look unattributed.
 */
const AdAttributions: React.FC = () => {
  const { studySlug } = useParams<{ studySlug: string }>();
  const { columns, rows, isLoading, isError, refetch, download, isDownloading } =
    useAdAttributions(studySlug);

  if (isLoading) {
    return <LoadingPage text="Loading ad attributions..." />;
  }

  if (isError) {
    return (
      <ErrorPlaceholder
        message="Failed to load ad attributions"
        onClickTryAgain={refetch}
      />
    );
  }

  return (
    <ConfWrapper>
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="sm:flex sm:items-center">
          <div className="sm:flex-auto">
            <h1 className="text-xl font-semibold text-gray-900">
              Ad attributions
            </h1>
            <p className="mt-2 text-sm text-gray-700">
              One row per ad this study has created, frozen as it was published.
              To recover a respondent's stratum, left-join your survey export on{' '}
              <code className="rounded bg-gray-100 px-1">ref_token</code> — which
              arrives in the response metadata as{' '}
              <code className="rounded bg-gray-100 px-1">vt</code>.
            </p>
          </div>
          {rows.length > 0 && (
            <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
              <button
                type="button"
                onClick={download}
                disabled={isDownloading}
                className="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
              >
                {isDownloading ? 'Downloading...' : 'Download CSV'}
              </button>
            </div>
          )}
        </div>

        {rows.length === 0 ? (
          // Legitimately empty before the first reconciliation run, so this
          // says which, rather than looking like a failure to load.
          <p className="mt-8 text-sm text-gray-600">
            No ads have been built for this study yet. Rows appear here once
            recruitment has run and created its first ads.
          </p>
        ) : (
          // Wide by nature — one column per stratum variable — so it scrolls
          // inside itself rather than pushing the page sideways.
          <div className="mt-8 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  {columns.map(c => (
                    <th
                      key={c}
                      scope="col"
                      className="whitespace-nowrap py-3 pr-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                    >
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {rows.map((row, i) => (
                  <tr key={`${row.network}-${row.ad_id}-${i}`}>
                    {columns.map(c => (
                      <td
                        key={c}
                        className="whitespace-nowrap py-2 pr-4 text-sm text-gray-700"
                      >
                        {row[c] || ''}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </ConfWrapper>
  );
};

export default AdAttributions;
