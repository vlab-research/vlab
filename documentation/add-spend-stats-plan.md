# Plan: Add Spend Stats to Recruitment Stats Tab

## Overview
Add three display-only stat cards to the recruitment stats tab showing: Total Spent, Ad Spent, and Incentive Spent. These will appear above the RecruitmentStatsTable.

## Current State
- **Location**: Recruitment stats tab in StudyPage
- **Current content**: Only shows the RecruitmentStatsTable with per-stratum metrics
- **Data available**: Per-stratum spend and incentive_cost already fetched via `recruitmentStats`
- **Existing components**: Stats component already exists and can be reused

## Implementation Approach

### 1. Create Display-Only Stats Component
**File**: `/home/nandan/Documents/vlab-research/vlab/dashboard/src/pages/StudyPage/components/DisplayStats.tsx` (NEW FILE)

Create a simplified version of the Stats component for display-only cards (no interactivity/selection):

```typescript
import { formatCurrency } from '../../../helpers/numbers';

interface DisplayStat {
  name: string;
  value: number;
}

const DisplayStats = ({ stats }: { stats: DisplayStat[] }) => {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {stats.map((stat) => (
        <div
          key={stat.name}
          className="bg-white shadow rounded-lg px-4 py-5 sm:p-6"
        >
          <dt className="text-sm font-medium truncate text-gray-500">
            {stat.name}
          </dt>
          <dd className="mt-1 text-3xl font-semibold text-gray-900">
            {formatCurrency(stat.value)}
          </dd>
        </div>
      ))}
    </div>
  );
};

export default DisplayStats;
```

**Key differences from Stats.tsx**:
- No `selectedStat` or `onSelectStat` props
- No hover effects or click handlers
- Grid uses `lg:grid-cols-3` (3 columns) instead of 4
- Simpler structure, focused on display only

### 2. Update RecruitmentStatsTable Component
**File**: `/home/nandan/Documents/vlab-research/vlab/dashboard/src/pages/StudyPage/components/RecruitmentStatsTable.tsx`

**Add imports**:
```typescript
import { useMemo } from 'react';
import DisplayStats from './DisplayStats';
```

**Add aggregation logic** (before the return statement, around line 90):
```typescript
const aggregatedStats = useMemo(() => {
  const strata = Object.values(data);
  return {
    totalSpent: strata.reduce((sum, s) => sum + s.total_cost, 0),
    adSpent: strata.reduce((sum, s) => sum + s.spend, 0),
    incentiveSpent: strata.reduce((sum, s) => sum + s.incentive_cost, 0),
  };
}, [data]);
```

**Add stat cards section** (between header and table, around line 110):
```typescript
<div className="mt-8">
  {/* Header with title and download button */}
  <div className="flex justify-between items-center mb-4">
    <h2 className="text-lg font-semibold">Recruitment Statistics</h2>
    <button ...>Download CSV</button>
  </div>

  {/* NEW: Display stat cards */}
  <div className="mb-6">
    <DisplayStats
      stats={[
        { name: 'Total Spent', value: aggregatedStats.totalSpent },
        { name: 'Ad Spent', value: aggregatedStats.adSpent },
        { name: 'Incentive Spent', value: aggregatedStats.incentiveSpent },
      ]}
    />
  </div>

  {/* Existing table */}
  <Table ...>
    ...
  </Table>
</div>
```

### 3. Handle Loading State (Optional but Recommended)
**File**: `/home/nandan/Documents/vlab-research/vlab/dashboard/src/pages/StudyPage/components/RecruitmentStatsTable.tsx`

Add a skeleton loader for the stat cards when data is loading:

```typescript
// Near the aggregatedStats useMemo
const hasData = Object.keys(data).length > 0;

// In the JSX, conditionally render skeleton or stats
{hasData ? (
  <div className="mb-6">
    <DisplayStats stats={[...]} />
  </div>
) : (
  <div className="mb-6">
    {/* Simple skeleton - three gray boxes */}
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-gray-100 animate-pulse rounded-lg h-24" />
      ))}
    </div>
  </div>
)}
```

**Alternative**: The loading state is already handled at the StudyPage level, so this might not be necessary.

## Critical Files to Modify/Create
1. `/home/nandan/Documents/vlab-research/vlab/dashboard/src/pages/StudyPage/components/DisplayStats.tsx` - NEW FILE
2. `/home/nandan/Documents/vlab-research/vlab/dashboard/src/pages/StudyPage/components/RecruitmentStatsTable.tsx` - MODIFY

## Important Considerations

### Grid Layout
- Uses 3 columns on large screens (`lg:grid-cols-3`) to accommodate 3 cards
- Responsive: 1 column mobile, 2 columns tablet, 3 columns desktop

### Data Source
- All data comes from existing `recruitmentStats` prop
- No new API calls needed
- Simple aggregation using `reduce()` to sum per-stratum values

### Formatting
- Use `formatCurrency` from `/home/nandan/Documents/vlab-research/vlab/dashboard/src/helpers/numbers.ts`
- Formats as USD with proper commas and decimals

### Loading State
- The parent component (StudyPage) already handles loading with `recruitmentStatsIsLoading`
- Shows `TableSkeleton` while loading
- Once loaded, both stat cards and table render together

### Empty State
- If no recruitment data exists, all three stats will show $0.00
- This is acceptable behavior

## Verification Steps

1. **Build the dashboard**: `cd dashboard && npm run build`
2. **Start the dev server**: `npm start`
3. **Navigate to a study page**
4. **Click on "Recruitment Statistics" tab**
5. **Verify the stat cards display**:
   - Three cards in a row on desktop
   - Shows: Total Spent, Ad Spent, Incentive Spent
   - Values are formatted as currency (e.g., $1,234.56)
   - Cards appear above the recruitment stats table
6. **Test responsive behavior**:
   - Mobile: Cards stack vertically (1 column)
   - Tablet: 2 columns
   - Desktop: 3 columns
7. **Test with different studies** to ensure aggregation works correctly
8. **Verify calculations**:
   - Total Spent = Ad Spent + Incentive Spent
   - Values match the sum of per-stratum data in the table below

## Trade-offs

**Pros**:
- Reuses existing design patterns (stat cards)
- Uses existing data (no new API calls)
- Simple aggregation logic
- Display-only keeps it simple
- Doesn't modify existing deviation stats

**Cons**:
- Creates a new component file (DisplayStats) instead of reusing Stats
  - Reason: Stats component requires selection/interaction logic we don't need
- Cards are display-only (not interactive)
  - Acceptable: There's no detail view or chart to show when clicked

## Alternative Approaches Considered

### Option A: Reuse Stats.tsx with dummy handlers
- Could pass empty `selectedStat=""` and `onSelectStat={() => {}}`
- **Rejected**: Would still show hover effects and cursor:pointer, confusing UX

### Option B: Modify Stats.tsx to support display-only mode
- Add optional prop like `displayOnly?: boolean`
- **Rejected**: Adds complexity to existing component for a single use case

### Option C: Use simple divs instead of a component
- Inline the card HTML in RecruitmentStatsTable
- **Rejected**: Less maintainable, harder to reuse if needed elsewhere

**Chosen approach (new DisplayStats component)**: Clean separation of concerns, reusable, simple.
