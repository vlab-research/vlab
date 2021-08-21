import { StudyProgressResource } from '../../types/study';
import SingleAreaChart, { SingleAreaChartSkeleton } from './SingleAreaChart';

const StudyProgressChart = ({
  label,
  data,
}: {
  label: string;
  data?: StudyProgressResource[];
}) => {
  if (!data) {
    return (
      <div className="pt-5 sm:pt-6 lg:pt-10">
        <SingleAreaChartSkeleton testId="study-progress-chart-skeleton" />
      </div>
    );
  }

  return (
    <div className="pt-5 sm:pt-6 lg:pt-10">
      <SingleAreaChart
        testId="study-progress-chart"
        label={label}
        data={data.map(resource => {
          const date = new Date(resource.datetime);
          date.setUTCHours(0);
          date.setUTCMinutes(0);
          date.setUTCSeconds(0);
          date.setUTCMilliseconds(0);

          return {
            primary: date,
            secondary:
              {
                'Current Participants': resource.currentParticipants,
                'Expected Participants': resource.expectedParticipants,
                'Current Avg. Deviation': resource.currentAverageDeviation,
                'Expected Avg. Deviation': resource.expectedAverageDeviation,
              }[label] || resource.currentParticipants,
          };
        })}
      />
    </div>
  );
};

export default StudyProgressChart;
