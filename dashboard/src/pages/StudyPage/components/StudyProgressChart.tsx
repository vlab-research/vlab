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
  if (label === 'Total Spent' && costData) {
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

  if (label === 'Avg Cost Per Participant' && costData) {
    // Filter out days with no new respondents
    const chartData = costData
      .filter(point => point.marginalCost !== null)
      .map(point => ({
        primary: new Date(point.datetime),
        secondary: point.marginalCost!,
      }));

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
