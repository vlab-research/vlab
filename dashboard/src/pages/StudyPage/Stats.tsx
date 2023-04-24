import { classNames, createSlugFor } from '../../helpers/strings';

const Stats = ({
  testId,
  stats,
  selectedStat,
  onSelectStat,
}: {
  testId?: string;
  stats: { name: string; stat: string }[];
  selectedStat: string;
  onSelectStat: (selectedStat: string) => void;
}) => (
  <StatsContainer testId={testId}>
    {stats.map(stat => (
      <Stat
        testId={`stats-card-for-${createSlugFor(stat.name)}`}
        key={stat.name}
        onClick={() => {
          onSelectStat(stat.name);
        }}
        selected={selectedStat === stat.name}
      >
        <StatName>{stat.name}</StatName>

        <dd
          className={classNames(
            'mt-1 text-3xl font-semibold',
            selectedStat === stat.name
              ? 'text-gray-900'
              : 'text-gray-500 group-hover:text-gray-700'
          )}
        >
          {stat.stat}
        </dd>
      </Stat>
    ))}
  </StatsContainer>
);

export const StatsSkeleton = ({
  statTestId,
  statNames,
  selectedStat,
}: {
  statTestId?: string;
  statNames: string[];
  selectedStat: string;
}) => (
  <StatsContainer>
    {statNames.map((statName, index) => (
      <Stat
        testId={statTestId}
        key={statName}
        selected={statName === selectedStat}
      >
        <StatName>{statName}</StatName>

        <div
          className="animate-pulse"
          style={{
            animationFillMode: 'backwards',
            animationDelay: `${150 * index}ms`,
          }}
        >
          <div className="mt-2 h-8 bg-gray-200 rounded w-24"></div>
        </div>
      </Stat>
    ))}
  </StatsContainer>
);

const StatsContainer = ({
  testId,
  children,
}: {
  testId?: string;
  children: React.ReactNode;
}) => (
  <dl
    className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4"
    data-testid={testId}
  >
    {children}
  </dl>
);

const Stat = ({
  testId,
  selected,
  children,
  onClick,
}: {
  testId?: string;
  selected: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}) => (
  <div
    data-testid={testId}
    onClick={onClick}
    className={classNames(
      'px-4 py-5 bg-white shadow rounded-lg overflow-hidden sm:p-6 group',
      onClick ? 'hover:bg-gray-50 cursor-pointer' : '',
      selected
        ? 'border-b-4 border-indigo-600'
        : 'border-b-4 border-transparent'
    )}
  >
    {children}
  </div>
);

const StatName = ({ children }: { children: string }) => (
  <dt className="text-sm font-medium truncate text-gray-500">{children}</dt>
);

export default Stats;
