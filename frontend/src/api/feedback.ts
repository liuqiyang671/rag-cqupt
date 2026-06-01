import { apiClient } from './client';
import type { FeedbackItem, FeedbackPayload } from '../types';

export async function submitFeedback(payload: FeedbackPayload): Promise<FeedbackItem> {
  const response = await apiClient.post<FeedbackItem>('/feedback', payload);
  return response.data;
}

export async function fetchFeedback(): Promise<FeedbackItem[]> {
  const response = await apiClient.get<FeedbackItem[]>('/feedback');
  return response.data;
}

