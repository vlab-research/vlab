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

// A click-to-WhatsApp destination. Shaped after Messenger, minus button_text
// (WhatsApp has no quick-reply button — the respondent gets a prefilled compose
// box) and plus the number the ad's clicks land on.
//
// include_metadata_in_ref is deliberately absent from the form. It defaults off
// in adopt, the autofill text is visible and editable by the respondent, and
// turning it on can make a study's refs unparseable by fly — which fails
// closed at config-save time rather than in the UI. Ship it as a form field
// only once there is a reason to.
export interface WhatsApp {
  type: string;
  name: string;
  initial_shortcode: string;
  welcome_message: string;
  whatsapp_phone_number: string;
  additional_metadata: Record<string, string> | null;
}

// One ad that opens either Messenger or WhatsApp, Meta choosing per respondent.
// Carries both arms' fields: button_text for the Messenger quick reply,
// whatsapp_phone_number for the WhatsApp promoted_object.
//
// Gated in adopt behind ADOPT_ENABLE_MULTI_DESTINATION until the WhatsApp arm
// is measured — see documentation/multi-destination-ads.md. Saving one while
// the gate is shut fails validation with an error that says so.
export interface Multi {
  type: string;
  name: string;
  initial_shortcode: string;
  welcome_message: string;
  button_text: string;
  whatsapp_phone_number: string;
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
