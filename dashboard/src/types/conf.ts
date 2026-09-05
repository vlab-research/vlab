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

// The recruitment union's tag. adopt discriminates on it (`RecruitmentConf` in
// adopt/adopt/study_conf.py); these three spellings are the ones this form has
// always written, which is why adopt adopted them rather than inventing others.
//
// Optional, because every conf stored before adopt started keeping the key has
// none: the server accepted it and `extra="ignore"` dropped it before storage.
// adopt infers the arm from shape when it is absent, so an old conf still
// loads and still saves.
export type RecruitmentType = 'simple' | 'pipeline_experiment' | 'destination';

export interface RecruitmentSimple {
  type?: RecruitmentType;
  ad_campaign_name: string;
  objective: string;
  optimization_goal: string;
  min_budget: number;
  budget: number;
  end_date: string;
  max_sample: number;
  start_date: string;
  incentive_per_respondent: number;
  efficiency_weight?: number;
}

export interface RecruitmentDestination {
  type?: RecruitmentType;
  ad_campaign_name_base: string;
  destinations: string[];
  objective: string;
  optimization_goal: string;
  min_budget: number;
  budget_per_arm: number;
  end_date: string;
  max_sample_per_arm: number;
  start_date: string;
  incentive_per_respondent: number;
  efficiency_weight?: number;
}

export interface PipelineExperiment {
  type?: RecruitmentType;
  ad_campaign_name_base: string;
  objective: string;
  optimization_goal: string;
  min_budget: number;
  budget_per_arm: number;
  end_date: string;
  max_sample_per_arm: number;
  start_date: string;
  arms: number;
  recruitment_days: number;
  offset_days: number;
  incentive_per_respondent: number;
  efficiency_weight?: number;
}

// What a destination's ad ref carries: the stratum inline ("metadata"), or an
// opaque token the ad-attributions export resolves back to it ("encoded").
//
// Optional on every type, and meaningfully so: absent means the conf predates
// the field and resolves to the behaviour it already has. Nothing writes a
// default onto such a conf — see forms/destinations/refMode.ts.
export type RefMode = 'metadata' | 'encoded';

export interface Messenger {
  type: string;
  name: string;
  initial_shortcode: string;
  welcome_message: string;
  button_text: string;
  additional_metadata: Record<string, string> | null;
  ref_mode?: RefMode;
}

export interface Web {
  type: string;
  name: string;
  url_template: string;
  ref_mode?: RefMode;
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
  ref_mode?: RefMode;
}

// A click-to-WhatsApp destination. Shaped after Messenger, minus button_text
// (WhatsApp has no quick-reply button — the respondent gets a prefilled compose
// box) and plus the number the ad's clicks land on.
export interface WhatsApp {
  type: string;
  name: string;
  initial_shortcode: string;
  welcome_message: string;
  whatsapp_phone_number: string;
  additional_metadata: Record<string, string> | null;
  ref_mode?: RefMode;
}

// One ad that opens either Messenger or WhatsApp, Meta choosing per respondent.
// Carries both arms' fields: button_text for the Messenger quick reply,
// whatsapp_phone_number for the WhatsApp promoted_object.
//
// The Messenger arm is measured against live Meta delivery; the WhatsApp arm is
// inferred from it by symmetry and has never been observed — see
// documentation/multi-destination-ads.md §4.
export interface Multi {
  type: string;
  name: string;
  initial_shortcode: string;
  welcome_message: string;
  button_text: string;
  whatsapp_phone_number: string;
  additional_metadata: Record<string, string> | null;
  ref_mode?: RefMode;
}

export type Destination = Messenger | Web | App | WhatsApp | Multi;

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
  // What the value read from `location` means: "raw" (it IS the answer) or
  // "ad_table_lookup" (it is an opaque token identifying the ad that recruited
  // the respondent). Optional because it post-dates every conf already stored,
  // and absent means "raw" everywhere that reads it.
  mapping?: string
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
