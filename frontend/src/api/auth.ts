import { apiClient } from './client';
import type { AuthResponse, LoginPayload, RegisterPayload, User } from '../types';

export async function register(payload: RegisterPayload): Promise<User> {
  const response = await apiClient.post<User>('/auth/register', payload);
  return response.data;
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>('/auth/login', payload);
  return response.data;
}

export async function getMe(): Promise<User> {
  const response = await apiClient.get<User>('/auth/me');
  return response.data;
}
