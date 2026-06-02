import { apiClient } from './client';
import type {
  KnowledgeImportOptions,
  KnowledgeImportResponse,
  KnowledgeItem,
  KnowledgePayload,
  KnowledgeStatsResponse,
} from '../types';

export async function fetchKnowledge(category?: string, limit = 1000): Promise<KnowledgeItem[]> {
  const response = await apiClient.get<KnowledgeItem[]>('/knowledge', {
    params: { ...(category ? { category } : {}), limit },
  });
  return response.data;
}

export async function fetchKnowledgeStats(): Promise<KnowledgeStatsResponse> {
  const response = await apiClient.get<KnowledgeStatsResponse>('/knowledge/stats');
  return response.data;
}

export async function createKnowledge(payload: KnowledgePayload): Promise<KnowledgeItem> {
  const response = await apiClient.post<KnowledgeItem>('/knowledge', payload);
  return response.data;
}

export async function updateKnowledge(id: number, payload: Partial<KnowledgePayload>): Promise<KnowledgeItem> {
  const response = await apiClient.put<KnowledgeItem>(`/knowledge/${id}`, payload);
  return response.data;
}

export async function deleteKnowledge(id: number): Promise<void> {
  await apiClient.delete(`/knowledge/${id}`);
}

export async function importKnowledgeDocument(
  file: File,
  options: KnowledgeImportOptions,
): Promise<KnowledgeImportResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('category', options.category);
  formData.append('source', options.source);
  formData.append('chunking_method', options.chunking_method);
  formData.append('chunk_size', String(options.chunk_size));
  formData.append('chunk_overlap', String(options.chunk_overlap));

  const response = await apiClient.post<KnowledgeImportResponse>('/knowledge/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}
