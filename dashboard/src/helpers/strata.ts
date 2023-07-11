import { Stratum, Variables, Creatives, Audiences, Level } from '../types/conf';

interface IntermediateLevel extends Level {
  variableName: string;
}

export const formatGroupProduct = (levels: IntermediateLevel[]) => {

  const tvars = levels.map(l => {
    return {
      "op": "equal",
      "vars": [
        { "type": "stratum", "value": `stratum_${l.variableName}` },
        { "type": "constant", "value": l.name },
      ],
    }
  })

  const idString = levels.map(l => `${l.variableName}:${l.name}`).join(",")

  const targeting = levels.reduce((a: any, l) => ({ ...a, ...l.facebook_targeting }), {}) // add baseTargeting

  const quota = levels.reduce((a: number, l) => a * l.quota, 1);


  return {
    id: idString,
    quota: quota,
    facebook_targeting: targeting,
    question_targeting: { "op": "and", "vars": [...tvars] }, // add finishFilter
  };

};


const cartesianProduct = (a: any[]) => {
  if (a.length === 1) {
    return a[0].map((l: any) => ([l]))
  }

  return a.reduce((a, b) => a.flatMap((d: any) => b.map((e: any) => [d, e].flat())));
}

export const createStrataFromVariables = (variables: Variables, creatives?: Creatives, audiences?: Audiences) => {
  if (!variables.length) return [];

  const allCreatives = creatives ? creatives.map((c: any) => c.name) : [];
  const allAudiences = audiences ? audiences.map((c: any) => c.name) : [];

  let res = variables
    .map((v: any) =>
      v.levels.map((level: any) => ({ ...level, variableName: v.name }))
    );

  const strata: Stratum[] = cartesianProduct(res)
    .map(formatGroupProduct)
    .map((data: Level) => ({
      audiences: allAudiences,
      excluded_audiences: [],
      metadata: {},
      creatives: allCreatives,
      ...data,
    }));

  return strata
}
