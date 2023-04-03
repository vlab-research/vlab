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
  instagram_id: string;
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

export interface Destination {
  ad_campaign_name_base: string;
  budget_per_arm: number;
  end_date: string;
  max_sample_per_arm: number;
  start_date: string;
}

export interface PipelineExperiment extends Destination {
  arms: number;
  recruitment_days: number;
  offset_days: number;
}

export type Conf = CreateStudy | General | Recruitment;
