import { api } from "./client";
import type { AuthTokens, User } from "../types";

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  company_name?: string;
  sector?: string;
  job_title?: string;
  company_size?: string;
  audit_reason?: string;
}
export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await api.post<User>("/api/v1/auth/register", payload);
  return data;
}

export async function login(email: string, password: string): Promise<AuthTokens> {
  const { data } = await api.post<AuthTokens>("/api/v1/auth/login", {
    email,
    password,
  });
  return data;
}

export async function logout(refreshToken: string): Promise<void> {
  await api.post("/api/v1/auth/logout", { refresh_token: refreshToken });
}
export async function verifyEmail(userId: string, code: string): Promise<User> {
  const { data } = await api.post<User>("/api/v1/auth/verify-email", {
    user_id: userId,
    code,
  });
  return data;
}

export async function resendVerification(email: string): Promise<User> {
  const { data } = await api.post<User>("/api/v1/auth/resend-verification", { email });
  return data;
}
export async function getMe(): Promise<User> {
  const { data } = await api.get<User>("/api/v1/auth/me");
  return data;
}

export async function uploadProfilePhoto(file: File): Promise<User> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<User>("/api/v1/auth/me/photo", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function removeProfilePhoto(): Promise<User> {
  const { data } = await api.delete<User>("/api/v1/auth/me/photo");
  return data;
}
export interface UpdateProfilePayload {
  full_name?: string | null;
  company_name?: string | null;
  sector?: string | null;
  job_title?: string | null;
  company_size?: string | null;
  audit_reason?: string | null;
}

export async function updateProfile(payload: UpdateProfilePayload): Promise<User> {
  const { data } = await api.patch<User>("/api/v1/auth/me", payload);
  return data;
}