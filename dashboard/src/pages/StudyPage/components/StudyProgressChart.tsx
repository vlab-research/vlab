import { StudyProgressResource, CostTimePointData } from '../../../types/study';
import SingleAreaChart, { SingleAreaChartSkeleton } from './SingleAreaChart';

const StudyProgressChart = ({
  label,
  data,
  costData,
}: {
  label: string;
  data?: StudyProgressResource[];
  costData?: CostTimePointData[];
}) => {
  if (!data && !costData) {
    return (
      <div className="pt-5 sm:pt-6 lg:pt-10">
        <SingleAreaChartSkeleton testId="study-progress-chart-skeleton" />
      </div>
    );
  }

  // Handle cost charts
  if (label === 'Total Spent') {
    if (!costData || costData.length === 0) {
      return (
        <div className="pt-5 sm:pt-6 lg:pt-10">
          <SingleAreaChartSkeleton testId="cumulative-spend-chart-skeleton" />
        </div>
      );
    }

    return (
      <div className="pt-5 sm:pt-6 lg:pt-10">
        <SingleAreaChart
          testId="cumulative-spend-chart"
          label={label}
          data={costData.map(point => ({
            primary: new Date(point.datetime),
            secondary: point.cumulativeSpend,
          }))}
        />
      </div>
    );
  }

  if (label === 'Avg Cost Per Participant') {
    if (!costData || costData.length === 0) {
      return (
        <div className="pt-5 sm:pt-6 lg:pt-10">
          <SingleAreaChartSkeleton testId="marginal-cost-chart-skeleton" />
        </div>
      );
    }

    // Filter out days with no new respondents
    const chartData = costData
      .filter(point => point.marginalCost !== null)
      .map(point => ({
        primary: new Date(point.datetime),
        secondary: point.marginalCost!,
      }));

    // If all marginal costs are null, show skeleton
    if (chartData.length === 0) {
      return (
        <div className="pt-5 sm:pt-6 lg:pt-10">
          <SingleAreaChartSkeleton testId="marginal-cost-chart-skeleton" />
        </div>
      );
    }

    return (
      <div className="pt-5 sm:pt-6 lg:pt-10">
        <SingleAreaChart
          testId="marginal-cost-chart"
          label={label}
          data={chartData}
        />
      </div>
    );
  }

  // Existing participant charts
  return (
    <div className="pt-5 sm:pt-6 lg:pt-10">
      <SingleAreaChart
        testId="study-progress-chart"
        label={label}
        data={data?.map(resource => {
          const date = new Date(resource.datetime);

          return {
            primary: date,
            secondary:
              {
                'Current Participants': resource.currentParticipants,
                'Expected Participants': resource.expectedParticipants,
              }[label] || resource.currentParticipants,
          };
        }) || []}
      />
    </div>
  );
};

export default StudyProgressChart;
