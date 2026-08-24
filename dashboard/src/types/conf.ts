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
  efficiency_weight?: number;
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
  efficiency_weight?: number;
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
  efficiency_weight?: number;
}

// How a destination's ads carry attribution. One question, same on every
// channel, because what a ref carries is a property of the ref rather than of
// the thing carrying it.
//
//   'encoded'  — the ref is an opaque token, and the stratum comes off the
//                ad-attributions export joined on it. The default for every new
//                destination. On a fly destination the token is packed with the
//                shortcode as `r.<payload>`, because fly's decoder needs both;
//                on web and app it travels as itself.
//   'metadata' — "thick": the ref carries the whole stratum inline, so it is
//                already in the response data and there is nothing to join.
//
// There is no third mode. A ref either carries the stratum or carries a token
// that resolves to it; "carry neither" attributes nobody and is not something
// anyone chooses. A study with no stratification simply gets a short ref,
// because there is nothing to put in it.
//
// Whether anything reads the token back is configured independently, in Data
// Extraction. The two sides do not constrain each other.
//
// Optional, and absent is meaningful: it means the conf was written before this
// field existed, which resolves to the inline ref. The form must never write a
// default onto a conf that arrived without one — see
// forms/destinations/refMode.ts.
export type RefMode = 'encoded' | 'metadata';

export interface Messenger {
  type: string;
  name: string;
  initial_shortcode: string;
  welcome_message: string;
  button_text: string;
  ref_mode?: RefMode;
  additional_metadata: Record<string, string> | null;
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
//
// The form always sends ref_mode. Worth knowing for this channel: the inline
// ref's autofill text sits in the respondent's compose box, visible and
// editable, and stratum values there can make a study's refs unparseable by fly
// — which fails closed at config-save time rather than in the UI.
export interface WhatsApp {
  type: string;
  name: string;
  initial_shortcode: string;
  welcome_message: string;
  whatsapp_phone_number: string;
  ref_mode?: RefMode;
  additional_metadata: Record<string, string> | null;
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
  ref_mode?: RefMode;
  additional_metadata: Record<string, string> | null;
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
