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
  { name: "Optimize", path: "optimize", component: Optimize },
]

export const pathLookup = Object.fromEntries(confs.map(({ component, path }) => [path, component]))

export const getNextConf = (conf: any) => {
  const i = confs.findIndex(c => c.path === conf);
  return confs[i + 1]?.path;
};
