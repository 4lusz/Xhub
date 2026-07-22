export interface AccountPortfolioSummary {
  twitter_account_id: string;
  username: string;
  display_name: string;
  profile_image_url: string | null;
  followers_count: number | null;
  followers_trend: number | null;
  impressions: number;
  likes: number;
  replies: number;
  reposts: number;
  impressions_trend: number | null;
  has_anomaly: boolean;
  has_enough_data: boolean;
}

export interface AccountMetricPoint {
  collected_at: string;
  followers_count: number | null;
}

export interface AccountPostSummary {
  post_account_id: string;
  post_id: string;
  text_preview: string;
  published_at: string;
  impression_count: number | null;
  like_count: number | null;
  reply_count: number | null;
  repost_count: number | null;
}

export interface AccountMetricsDetail {
  twitter_account_id: string;
  username: string;
  display_name: string;
  followers_history: AccountMetricPoint[];
  top_posts: AccountPostSummary[];
}

export interface PostMetricPoint {
  collected_at: string;
  impression_count: number | null;
  like_count: number | null;
  reply_count: number | null;
  repost_count: number | null;
}

export interface PostAccountMetricsDetail {
  post_account_id: string;
  twitter_account_id: string;
  username: string;
  published_at: string;
  history: PostMetricPoint[];
}
