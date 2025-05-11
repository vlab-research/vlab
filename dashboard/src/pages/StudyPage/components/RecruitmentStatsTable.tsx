import React, { useState } from 'react';
import { RecruitmentStatsRow } from '../../../types/study';
import Table from './Table';
import { formatCurrency, formatNumber, formatPercentage } from '../../../helpers/numbers';

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
    'Spend',
    'Impressions',
    'Reach',
    'CPM',
    'Unique Clicks',
    'Unique CTR',
    'Respondents',
    'Price per Respondent',
    'Incentive Cost',
    'Total Cost',
    'Conversion Rate',
  ];

  const rows = Object.entries(data).map(([stratumId, stats]) => ({
    id: stratumId,
    values: [
      stratumId,
      formatCurrency(stats.spend),
      formatNumber(stats.impressions),
      formatNumber(stats.reach),
      formatCurrency(stats.cpm),
      formatNumber(stats.unique_clicks),
      formatPercentage(stats.unique_ctr),
      formatNumber(stats.respondents),
      formatCurrency(stats.price_per_respondent),
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

  return (
    <div className="mt-8">
      <h2 className="text-lg font-semibold mb-4">Recruitment Statistics</h2>
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