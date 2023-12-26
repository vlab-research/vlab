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

export type Recruitment = RecruitmentSimple | Destination | PipelineExperiment;

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
}

export interface RecruitmentDestination {
  ad_campaign_name_base: string;
  destination: string;
  objective: string;
  optimization_goal: string;
  destination_type: string;
  min_budget: number;
  budget_per_arm: number;
  end_date: string;
  max_sample_per_arm: number;
  start_date: string;
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
}

export interface Messenger {
  type: string;
  name: string;
  initial_shortcode: string;
  welcome_message: string;
  button_text: string;
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

export type Audience = {
  name: string;
  subtype: string;
};

export type Audiences = Audience[];

export type LocalFormData =
  | CreateStudy
  | General
  | Recruitment
  | Audiences
  | Destinations
  | Creatives
  | Variables
  | Strata;

export type GlobalFormData = {
  general: General;
  recruitment: Recruitment;
  destinations: Destinations;
  audiences: Audiences;
  creatives: Creatives;
  variables: Variables;
  strata: Strata;
};
