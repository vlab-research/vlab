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

export type Conf = CreateStudy | General;
