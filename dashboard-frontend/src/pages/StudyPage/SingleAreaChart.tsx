import React from 'react';
import { AxisOptions, Chart } from 'react-charts';

type DataPoint = {
  primary: Date;
  secondary: number;
};

const SingleAreaChart = ({
  label,
  data,
  testId,
}: {
  label: string;
  data: DataPoint[];
  testId?: string;
}) => {
  const primaryAxis = React.useMemo<AxisOptions<DataPoint>>(
    () => ({
      getValue: datum => datum.primary,
      tickCount: 10,
      showGrid: false,
    }),
    []
  );

  const secondaryAxes = React.useMemo<AxisOptions<DataPoint>[]>(
    () => [
      {
        getValue: datum => datum.secondary,
        tickCount: 5,
        elementType: 'area',
      },
    ],
    []
  );

  return (
    <div data-testid={testId} className="h-80 bg-white rounded-lg p-4">
      <div className="h-full w-full">
        <Chart
          options={{
            data: [
              {
                label,
                data,
              },
            ],
            getSeriesStyle: series => ({
              color: '#4F46E5',
              area: {
                fill: '#E0E7FF',
              },
            }),
            primaryAxis,
            secondaryAxes,
          }}
        />
      </div>
    </div>
  );
};

export const SingleAreaChartSkeleton = ({ testId }: { testId?: string }) => (
  <div data-testid={testId} className="h-80 bg-white rounded-lg p-4">
    <div className="h-full w-full"></div>
  </div>
);

export default SingleAreaChart;
