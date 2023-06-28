export interface CreateStudy {
  name: string;
}

export interface General {
  objective: string;
  optimization_goal: string;
  destination_type: string;
  page_id: string;
  min_budget: number;
  opt_window: number;
  instagram_id?: string | undefined;
  ad_account: string;
}

export type Recruitment = RecruitmentSimple | Destination | PipelineExperiment;

export interface RecruitmentSimple {
  ad_campaign_name: string;
  budget: number;
  end_date: string;
  max_sample: number;
  start_date: string;
}

export interface RecruitmentDestination {
  ad_campaign_name_base: string;
  budget_per_arm: number;
  end_date: string;
  max_sample_per_arm: number;
  start_date: string;
}

export interface PipelineExperiment extends RecruitmentDestination {
  arms: number;
  recruitment_days: number;
  offset_days: number;
}
export interface Messenger {
  name: string;
  initial_shortcode: string;
  type: string;
}

export interface Web {
  name: string;
  url_template: string;
  type: string;
}
export interface App {
  name: string;
  app_install_state: string;
  app_install_link: string;
  facebook_app_id: string;
  deeplink_template: string;
  user_device: string[];
  user_os: string[];
  type: string;
}

export type Destination = Messenger | Web | App;

export type Destinations = Destination[];

export type Creative = {
  name: string;
  body: string;
  button_text?: string | undefined;
  destination: string;
  image_hash: string;
  link_text: string;
  welcome_message?: string | undefined;
  tags: null;
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
  metadata: [string, string];
};

export type Strata = Stratum[];

export type LocalFormData =
  | CreateStudy
  | General
  | Recruitment
  | Destinations
  | Creatives
  | Strata;

export type GlobalFormData = {
  general: General;
  recruitment: Recruitment;
  destinations: Destinations;
  creatives: Creatives;
  strata: Strata;
};
