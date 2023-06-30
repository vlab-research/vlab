import React from 'react';
import { GlobalFormData } from '../../../../types/conf';

interface Props {
  globalData: GlobalFormData;
}

const Variables: React.FC<Props> = ({ globalData }: Props) => {
  const creatives = globalData.creatives
    ? globalData.creatives.map((c: any) => c.name)
    : [];

  const strata = globalData.variables
    ?.flatMap((x: any) =>
      x.levels.map((y: any) => ({ ...y, id: `${x.name}-${y.name}` }))
    )
    .map(data => ({
      audiences: [],
      excluded_audiences: [],
      metadata: {},
      creatives: creatives,
      ...data,
    }))
    .map(d => {
      delete d.name;
      delete d.adset_id;
      return d;
    });

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <p> UNDER CONSTRUCTION </p>
        {strata?.map(s => (
          <p>{JSON.stringify(s)} </p>
        ))}
      </div>
    </div>
  );
};

export default Variables;
