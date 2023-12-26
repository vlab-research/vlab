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

export const createStrataFromVariables = (variables: Variables, finishQuestionRef?: string, creatives?: Creatives, audiences?: Audiences) => {
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

  const strata: Stratum[] = cartesianProduct(res)
    .map((l: IntermediateLevel[]) => formatGroupProduct(l, finishQuestionRef))
    .map((data: Level) => ({
      audiences: [], // TODO: ADD AUDIENCES SOMEHOW??
      excluded_audiences: allAudiences[0] ? [allAudiences[0]] : [], // TODO: ADD EXLUDED AUDIENCE SOMEHOW??
      creatives: allCreatives,
      ...data,
    }));

  return strata
}

export const getFinishQuestionRef = (strata: Stratum[]): string => {
  const s = strata[0]

  if (!s) return ""

  const finishFilter = s.question_targeting.vars.find((v: any) => v.op === "answered")
  const ref = finishFilter.vars[0].value
  return ref
}
