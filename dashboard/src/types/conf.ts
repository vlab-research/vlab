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

// How a destination's ads carry attribution.
//
//   'encoded'  — the ref is `r.<token>`: clean, and attributes via the
//                ad_attributions join on ref_token. The default for every new
//                destination, on every channel.
//   'metadata' — "thick": the ref carries the whole stratum inline. Correct and
//                free on Messenger, where the ref is invisible; Messenger-only,
//                because on WhatsApp it sits in the respondent's compose box.
//
// A third mode, 'shortcode' (a clean ref that attributes nobody), exists in
// adopt's RefMode literal and is deliberately not in this union: it is not
// offered by the form. It stays resolvable in adopt because an old conf with
// ref_mode absent resolves to it from the legacy include_metadata_in_ref flag.
//
// Optional, and absent is meaningful: it means the conf was written before this
// field existed, and adopt resolves it per channel from that legacy flag. The
// form must never write a default onto a conf that arrived without one — see
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
