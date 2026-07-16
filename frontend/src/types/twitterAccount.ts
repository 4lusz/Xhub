export interface TwitterAccount {
  id: string;
  user_id: string;
  twitter_user_id: string;
  username: string;
  display_name: string;
  /** Foto de perfil real da conta do X. `null` para contas conectadas antes desta funcionalidade. */
  profile_image_url: string | null;
  expires_at: string;
  created_at: string;
  updated_at: string;
}
