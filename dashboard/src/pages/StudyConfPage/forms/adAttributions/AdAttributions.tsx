import React from 'react';
import { useParams } from 'react-router-dom';
import ConfWrapper from '../../components/ConfWrapper';
import LoadingPage from '../../../../components/LoadingPage';
import ErrorPlaceholder from '../../../../components/ErrorPlaceholder';
import useAdAttributions from '../../hooks/useAdAttributions';
import { JOIN_COLUMN, csvFilename, toCsv } from './adAttributions';
import { AdAttributionsTable } from '../../../../types/study';

const download = (table: AdAttributionsTable, studySlug: string) => {
  const url = URL.createObjectURL(
    new Blob([toCsv(table)], { type: 'text/csv' })
  );
  const a = document.createElement('a');
  a.href = url;
  a.download = csvFilename(studySlug);
  a.click();
  URL.revokeObjectURL(url);
};

const AdAttributions: React.FC = () => {
  const { studySlug } = useParams<{ studySlug: string }>();
  const { table, isLoading, isError, refetch } = useAdAttributions(studySlug);

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
              Ad Attributions
            </h1>
            <p className="mt-2 text-sm text-gray-700">
              One row per ad this study created, frozen with the creative and
              stratum it was published with. Left-join your survey export on{' '}
              <code>{JOIN_COLUMN}</code> and your stratum columns come back,
              named as they always were.
            </p>
            <p className="mt-2 text-sm text-gray-500">
              Ads this study no longer runs are here too: respondents keep
              arriving from deleted ads through reshared posts, and a row
              missing here would look like an unattributed respondent.
            </p>
          </div>
          {table.rows.length > 0 && (
            <div className="mt-4 sm:mt-0 sm:ml-8 sm:flex-none">
              <button
                type="button"
                onClick={() => download(table, studySlug)}
                className="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700"
              >
                Download CSV
              </button>
            </div>
          )}
        </div>

        {table.rows.length === 0 ? (
          <p className="mt-8 text-sm text-gray-600">
            No ads yet. A row lands here the moment vlab creates an ad for this
            study.
          </p>
        ) : (
          <div className="mt-8 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  {table.columns.map(c => (
                    <th
                      key={c}
                      scope="col"
                      className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                    >
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {table.rows.map((row, i) => (
                  <tr key={i}>
                    {table.columns.map(c => (
                      <td
                        key={c}
                        className="whitespace-nowrap px-3 py-2 text-sm text-gray-900"
                      >
                        {row[c]}
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
