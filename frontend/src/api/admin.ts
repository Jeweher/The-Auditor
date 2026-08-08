import { api } from "./client";
import type { User } from "../types";

export async function listUsers(): Promise<User[]> {
  const { data } = await api.get<User[]>("/api/v1/admin/users");
  return data;
}

export async function updateUserActive(userId: string, isActive: boolean): Promise<User> {
  const { data } = await api.patch<User>(`/api/v1/admin/users/${userId}/active`, {
    is_active: isActive,
  });
  return data;
}

export async function updateUserRole(userId: string, role: "user" | "admin"): Promise<User> {
  const { data } = await api.patch<User>(`/api/v1/admin/users/${userId}/role`, { role });
  return data;
}