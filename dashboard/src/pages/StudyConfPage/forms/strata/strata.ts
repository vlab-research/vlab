import isEqual from 'lodash/isEqual';
import { Stratum, Variables, Creatives, Audiences, Level } from '../../../../types/conf';

interface IntermediateLevel extends Level {
  variableName: string;
}

export const formatGroupProduct = (levels: IntermediateLevel[], finishQuestionRef: string) => {

  const tvars = levels.map(l => {
    return {
      "op": "equal",
      "vars": [
        { "type": "variable", "value": `${l.variableName}` },
        { "type": "constant", "value": l.name },
      ],
    }
  })

  const metadata = levels.map(l => ({ [l.variableName]: l.name })).reduce((a, b) => ({ ...a, ...b }))

  const idString = levels.map(l => `${l.variableName}:${l.name}`).join(",")

  const targeting = levels.reduce((a: any, l) => ({ ...a, ...l.facebook_targeting }), {}) // add baseTargeting

  const quota = levels.reduce((a: number, l) => a * l.quota, 1);

  const finishFilter = {
    "op": "answered",
    "vars": [{ "type": "variable", "value": finishQuestionRef }],
  }


  return {
    id: idString,
    quota: quota,
    facebook_targeting: targeting,
    metadata: metadata,
    question_targeting: { "op": "and", "vars": [...tvars, finishFilter] },
  };

};


const cartesianProduct = (a: any[]) => {
  if (a.length === 1) {
    return a[0].map((l: any) => ([l]))
  }

  return a.reduce((a, b) => a.flatMap((d: any) => b.map((e: any) => [d, e].flat())));
}

export const createStrataFromVariables = (
  variables: Variables,
  finishQuestionRef?: string,
  creatives?: Creatives,
  audiences?: Audiences,
  existingStrata?: Stratum[]
) => {
  if (!variables.length) return [];

  if (!finishQuestionRef) {
    return []
  }

  const allCreatives = creatives ? creatives.map((c: any) => c.name) : [];
  const allAudiences = audiences ? audiences.map((c: any) => c.name) : [];

  let res = variables
    .map((v: any) =>
      v.levels.map((level: any) => ({ ...level, variableName: v.name }))
    );

  const newStrata: Stratum[] = cartesianProduct(res)
    .map((l: IntermediateLevel[]) => formatGroupProduct(l, finishQuestionRef))
    .map((data: Level) => ({
      audiences: [],
      excluded_audiences: allAudiences,
      creatives: allCreatives,
      ...data,
    }));

  // If no existing strata provided, return new strata as-is
  if (!existingStrata || existingStrata.length === 0) {
    return newStrata;
  }

  // Merge by stratum ID: preserve user-edited fields from existing strata,
  // overwrite derived fields (facebook_targeting) with fresh values
  const existingById = new Map(existingStrata.map(s => [s.id, s]));

  return newStrata.map(newStratum => {
    const existing = existingById.get(newStratum.id);
    if (!existing) {
      return newStratum;
    }

    // Preserve user-edited fields: creatives, audiences, excluded_audiences, quota, metadata
    // Overwrite derived fields: facebook_targeting, question_targeting
    return {
      ...newStratum,
      creatives: existing.creatives,
      audiences: existing.audiences,
      excluded_audiences: existing.excluded_audiences,
      quota: existing.quota,
      metadata: existing.metadata,
    };
  });
}

export const strataStalenessHint = (variables: Variables, savedStrata?: Stratum[]): boolean => {
  if (!savedStrata || savedStrata.length === 0) {
    return variables.length > 0;
  }

  // Generate what the strata would be from current variables (without merging)
  // Use a dummy finishQuestionRef if one doesn't exist in savedStrata
  let finishRef = getFinishQuestionRef(savedStrata);
  if (!finishRef) {
    finishRef = "dummy";
  }

  const freshStrata = createStrataFromVariables(variables, finishRef);

  // Check 1: different set of stratum IDs
  const savedIds = savedStrata.map(s => s.id);
  const freshIds = freshStrata.map(s => s.id);

  if (savedIds.length !== freshIds.length) {
    return true;
  }

  for (const id of savedIds) {
    if (!freshIds.includes(id)) {
      return true;
    }
  }

  // Check 2: facebook_targeting changed for any stratum that exists in both.
  // Use deep equality rather than JSON.stringify so that backend JSON key-order
  // differences (Go sorts map keys alphabetically) don't falsely flag strata as stale.
  for (const savedStratum of savedStrata) {
    const freshStratum = freshStrata.find(s => s.id === savedStratum.id);
    if (freshStratum && !isEqual(freshStratum.facebook_targeting, savedStratum.facebook_targeting)) {
      return true;
    }
  }

  return false;
};

export const getFinishQuestionRef = (strata: Stratum[]): string => {
  const s = strata[0]

  if (!s) return ""

  const finishFilter = s.question_targeting.vars.find((v: any) => v.op === "answered")
  const ref = finishFilter.vars[0].value
  return ref
}
