export interface CreateStudy {
  name: string;
}

export interface General {
  name: string;
  credentials_key: string;
  credentials_entity: string;
  ad_account: string;
  opt_window: number;
}

export type Recruitment = RecruitmentSimple | RecruitmentDestination | PipelineExperiment;

export interface RecruitmentSimple {
  ad_campaign_name: string;
  objective: string;
  optimization_goal: string;
  destination_type: string;
  min_budget: number;
  budget: number;
  end_date: string;
  max_sample: number;
  start_date: string;
  incentive_per_respondent: number;
}

export interface RecruitmentDestination {
  ad_campaign_name_base: string;
  destinations: string[];
  objective: string;
  optimization_goal: string;
  destination_type: string;
  min_budget: number;
  budget_per_arm: number;
  end_date: string;
  max_sample_per_arm: number;
  start_date: string;
  incentive_per_respondent: number;
}

export interface PipelineExperiment {
  ad_campaign_name_base: string;
  objective: string;
  optimization_goal: string;
  destination_type: string;
  min_budget: number;
  budget_per_arm: number;
  end_date: string;
  max_sample_per_arm: number;
  start_date: string;
  arms: number;
  recruitment_days: number;
  offset_days: number;
  incentive_per_respondent: number;
}

export interface Messenger {
  type: string;
  name: string;
  initial_shortcode: string;
  welcome_message: string;
  button_text: string;
  additional_metadata: Record<string, string> | null;
}

export interface Web {
  type: string;
  name: string;
  url_template: string;

}
export interface App {
  type: string;
  name: string;
  app_install_state: string;
  app_install_link: string;
  facebook_app_id: string;
  deeplink_template: string;
  user_device: string[];
  user_os: string[];
}

export type Destination = Messenger | Web | App;

export type Destinations = Destination[];

export type Creative = {
  name: string;
  destination: string;
  template: any; // TODO: create a type for facebook adcreative (stubs?)
  template_campaign: string;
};

export type Creatives = Creative[];


export type Audience = {
  name: string;
  subtype: string;
};

export type Audiences = Audience[];


export type Level = {
  name: string;
  template_campaign: string;
  template_adset: string;
  facebook_targeting: any;
  quota: number;
};

export type Variable = {
  name: string;
  properties: string[];
  levels: Level[];
};

export type Variables = Variable[];


export type Stratum = {
  id: string;
  quota: number;
  creatives: string[];
  audiences: string[];
  excluded_audiences: string[];
  facebook_targeting: any; // TODO create a type for facebook targeting
  question_targeting?: any; // TODO create a type for question targeting
  metadata: any;
};

export type Strata = Stratum[];


export type FlyConfig = {
  survey_name: string;
}

export type QualtricsConfig = {
  survey_id: string;
}

export type TypeformConfig = {
  form_id: string;
}


export type AlchemerConfig = {
  survey_id: string;
  timezone: string;
}

export type DataSourceConfig = FlyConfig | QualtricsConfig | TypeformConfig;

export type DataSource = {
  name: string;
  source: string;
  credentials_key: string;
  config: DataSourceConfig;
};

export type DataSources = DataSource[];

export type ExtractionFunction = {
  function: string;
  params?: any;
}

export type Extraction = {
  location: string
  key: string
  name: string
  functions: ExtractionFunction[]
  value_type: string
  aggregate: string
}

export type SourceExtraction = {
  extraction_confs: Extraction[];
  user_variable?: string;
}

export type InferenceData = {
  data_sources: Record<string, SourceExtraction>
}


export type LocalFormData =
  | CreateStudy
  | General
  | Recruitment
  | Audiences
  | Destinations
  | Creatives
  | Variables
  | Strata
  | DataSources
  | InferenceData;

export type FormTypes =
  | "general"
  | "recruitment"
  | "destinations"
  | "audiences"
  | "creatives"
  | "variables"
  | "strata"
  | "data_sources"

export type GlobalFormData = {
  general: General;
  recruitment: Recruitment;
  destinations: Destinations;
  audiences: Audiences;
  creatives: Creatives;
  variables: Variables;
  strata: Strata;
  data_sources: DataSources;
};

export type CopyFromConf = {
  source_study_slug: string;
}
