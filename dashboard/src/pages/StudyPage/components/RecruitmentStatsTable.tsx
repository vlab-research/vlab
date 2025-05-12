import React, { useState } from 'react';
import { RecruitmentStatsRow } from '../../../types/study';
import Table from './Table';
import { formatCurrency, formatNumber, formatPercentage } from '../../../helpers/numbers';
import { DownloadIcon } from '@heroicons/react/solid';

interface RecruitmentStatsTableProps {
  data: {
    [stratumId: string]: RecruitmentStatsRow;
  };
}

const RecruitmentStatsTable: React.FC<RecruitmentStatsTableProps> = ({ data }) => {
  const [selectedColumn, setSelectedColumn] = useState({
    index: 0,
    hasDescendingOrder: false,
  });

  const columnNames = [
    'Stratum',
    'Frequency',
    'Reach',
    'CPM',
    'Unique Clicks',
    'Unique CTR',
    'Respondents',
    'Price per Respondent',
    'Ad Cost',
    'Incentive Cost',
    'Total Cost',
    'Conversion Rate',
  ];

  const rows = Object.entries(data).map(([stratumId, stats]) => ({
    id: stratumId,
    values: [
      stratumId,
      formatNumber(stats.frequency),
      formatNumber(stats.reach),
      formatCurrency(stats.cpm),
      formatNumber(stats.unique_clicks),
      formatPercentage(stats.unique_ctr),
      formatNumber(stats.respondents),
      formatCurrency(stats.price_per_respondent),
      formatCurrency(stats.spend),
      formatCurrency(stats.incentive_cost),
      formatCurrency(stats.total_cost),
      formatPercentage(stats.conversion_rate),
    ],
  }));

  const pagination = {
    from: 1,
    to: rows.length,
    total: rows.length,
    previousButton: {
      disabled: true,
      onClick: () => {},
    },
    nextButton: {
      disabled: true,
      onClick: () => {},
    },
  };

  const handleDownloadCSV = () => {
    // Create CSV header
    const header = columnNames.join(',');
    
    // Create CSV rows
    const csvRows = rows.map(row => {
      // Remove currency symbols and commas from values for proper CSV formatting
      return row.values.map(value => {
        // Remove currency symbol and commas, and wrap in quotes to handle any special characters
        const cleanValue = value.replace(/[$,]/g, '');
        return `"${cleanValue}"`;
      }).join(',');
    });

    // Combine header and rows
    const csvContent = [header, ...csvRows].join('\n');

    // Create blob and download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', 'recruitment_stats.csv');
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="mt-8">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Recruitment Statistics</h2>
        <button
          onClick={handleDownloadCSV}
          className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          <DownloadIcon className="-ml-1 mr-2 h-5 w-5 text-gray-500" aria-hidden="true" />
          Download CSV
        </button>
      </div>
      <Table
        columnNames={columnNames}
        rows={rows}
        pagination={pagination}
        selectedColumn={{
          ...selectedColumn,
          onChange: (newIndex: number) => {
            setSelectedColumn({
              index: newIndex,
              hasDescendingOrder: selectedColumn.index === newIndex ? !selectedColumn.hasDescendingOrder : false,
            });
          },
        }}
      />
    </div>
  );
};

export default RecruitmentStatsTable; 