export interface UserProfile {
  username: string;
  display_name?: string | null;
  retention_days?: number | null;
}

export interface AuthResponse {
  token: string;
  profile: UserProfile;
}
