import React from 'react';
import SimpleTable from '../../../../components/Table';
import ConfWrapper from '../../components/ConfWrapper';
import { useParams } from 'react-router-dom';
import LoadingPage from '../../../../components/LoadingPage';
import ErrorPlaceholder from '../../../../components/ErrorPlaceholder';
import useCurrentData from '../../hooks/useCurrentData';
import { GlobalFormData } from '../../../../types/conf';
import { CurrentDataRow } from '../../../../types/study';

interface Props {
  globalData: GlobalFormData;
}

const CurrentData: React.FC<Props> = () => {
  const { studySlug } = useParams<{ studySlug: string }>();
  const { data, isLoading, isError, refetch } = useCurrentData(studySlug);

  if (isLoading) {
    return <LoadingPage text="Loading current data..." />;
  }

  if (isError) {
    return (
      <ErrorPlaceholder
        message="Failed to load current data"
        onClickTryAgain={refetch}
      />
    );
  }

  // Ensure data is always an array
  const tableData: CurrentDataRow[] = data || [];

  return (
    <ConfWrapper>
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="sm:flex sm:items-center">
          <div className="sm:flex-auto">
            <h1 className="text-xl font-semibold text-gray-900">Current Data</h1>
            <p className="mt-2 text-sm text-gray-700">
              Current data extracted and used for optimization
            </p>
          </div>
        </div>
        <div className="mt-8">
          <SimpleTable data={tableData} />
        </div>
      </div>
    </ConfWrapper>
  );
};

export default CurrentData; 