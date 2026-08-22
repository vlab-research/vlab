import General from './forms/general/General';
import Recruitment from './forms/recruitment/Recruitment';
import Destinations from './forms/destinations/Destinations';
import Creatives from './forms/creatives/Creatives';
import Variables from './forms/variables/Variables';
import Audiences from './forms/audience/Audiences';
import Strata from './forms/strata/Strata';
import DataSources from './forms/dataSources/DataSources';
import InferenceData from './forms/inferenceData/InferenceData';
import Initialize from './forms/initialize/Initialize';
import Optimize from './forms/optimize/Optimize';
import CurrentData from './forms/current/CurrentData';
import StudyErrors from './forms/errors/StudyErrors';
import AdAttributions from './forms/adAttributions/AdAttributions';


export const confs = [
  { name: "Initialize", path: "initialize", component: Initialize },
  { name: "General", path: "general", component: General },
  { name: "Recruitment", path: "recruitment", component: Recruitment },
  { name: "Destinations", path: "destinations", component: Destinations },
  { name: "Creatives", path: "creatives", component: Creatives },
  { name: "Audiences", path: "audiences", component: Audiences },
  { name: "Variables", path: "variables", component: Variables },
  { name: "Strata", path: "strata", component: Strata },
  { name: "Data Sources", path: "data-sources", component: DataSources },
  { name: "Data Extraction", path: "inference-data", component: InferenceData },
  { name: "Current Data", path: "current-data", component: CurrentData },
  // A confirmation surface rather than a configuration step, so it sits with
  // the views of what the study has done rather than with the forms that
  // precede a run. Note this array doubles as the wizard's next-step chain
  // (getNextConf), so inserting here changes where Current Data advances to.
  { name: "Ad Attributions", path: "ad-attributions", component: AdAttributions },
  { name: "Errors", path: "errors", component: StudyErrors },
  { name: "Optimize", path: "optimize", component: Optimize },
]

export const pathLookup = Object.fromEntries(confs.map(({ component, path }) => [path, component]))

export const getNextConf = (conf: any) => {
  const i = confs.findIndex(c => c.path === conf);
  return confs[i + 1]?.path;
};

export type FormTypes =
  | 'initialize'
  | 'general'
  | 'recruitment'
  | 'destinations'
  | 'creatives'
  | 'audiences'
  | 'variables'
  | 'strata'
  | 'data-sources'
  | 'inference-data'
  | 'optimize'
  | 'current-data'
  | 'ad-attributions'
  | 'errors';
