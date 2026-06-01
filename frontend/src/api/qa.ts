import { apiClient } from './client';
import type {
  AskResponse,
  ConversationSession,
  ConversationSessionListResponse,
  KnowledgeItem,
  QARecord,
  QARecordListResponse,
} from '../types';

export async function askQuestion(question: string, sessionId?: number): Promise<AskResponse> {
  const response = await apiClient.post<AskResponse>('/qa/ask', {
    question,
    ...(sessionId ? { session_id: sessionId } : {}),
  });
  return response.data;
}

export interface StreamCallbacks {
  onMetadata: (data: {
    retrieved_context: KnowledgeItem[];
    model_provider: string;
    session_id: number;
    conversation_summary: string;
  }) => void;
  onChunk: (content: string) => void;
  onDone: (data: { qa_record_id: number; session_id: number; conversation_summary: string }) => void;
  onError: (error: Error) => void;
}

export async function askQuestionStream(
  question: string,
  callbacks: StreamCallbacks,
  sessionId?: number,
): Promise<void> {
  const baseURL = import.meta.env.VITE_API_BASE_URL ?? '/api';
  const token = localStorage.getItem('token');
  let response: Response;
  try {
    response = await fetch(`${baseURL}/qa/ask/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        question,
        ...(sessionId ? { session_id: sessionId } : {}),
      }),
    });
    if (!response.ok) {
      throw new Error(await getStreamErrorMessage(response));
    }
  } catch (error) {
    callbacks.onError(error instanceof Error ? error : new Error(String(error)));
    return;
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop()!;
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'metadata') {
            callbacks.onMetadata(data);
          } else if (data.type === 'chunk') {
            callbacks.onChunk(data.content);
          } else if (data.type === 'done') {
            callbacks.onDone(data);
          } else if (data.type === 'error') {
            callbacks.onError(new Error(data.message || '模型或 Embedding 服务不可用。'));
            return;
          }
        } catch {
          // skip malformed JSON lines
        }
      }
    }
  } catch (error) {
    callbacks.onError(error instanceof Error ? error : new Error(String(error)));
  }
}

async function getStreamErrorMessage(response: Response): Promise<string> {
  try {
    const payload = await response.clone().json();
    if (typeof payload?.detail === 'string') {
      return payload.detail;
    }
  } catch {
    // fall back to status-based messages
  }
  if (response.status === 401) {
    return '登录状态已失效，请重新登录。';
  }
  return `问答请求失败：HTTP ${response.status}`;
}

export async function getQARecords(
  status: string = 'active',
  skip: number = 0,
  limit: number = 20
): Promise<QARecordListResponse> {
  const response = await apiClient.get('/qa/records', {
    params: { status, skip, limit }
  });
  return response.data;
}

export async function getConversationSessions(
  status: string = 'active',
  skip: number = 0,
  limit: number = 20,
): Promise<ConversationSessionListResponse> {
  const response = await apiClient.get('/qa/sessions', {
    params: { status, skip, limit },
  });
  return response.data;
}

export async function getConversationSessionRecords(sessionId: number): Promise<QARecordListResponse> {
  const response = await apiClient.get(`/qa/sessions/${sessionId}/records`);
  return response.data;
}

export async function archiveSession(id: number): Promise<ConversationSession> {
  const response = await apiClient.put(`/qa/sessions/${id}/archive`);
  return response.data;
}

export async function deleteSession(id: number): Promise<void> {
  await apiClient.delete(`/qa/sessions/${id}`);
}

export async function getQARecord(id: number): Promise<QARecord> {
  const response = await apiClient.get(`/qa/records/${id}`);
  return response.data;
}

export async function archiveRecord(id: number): Promise<QARecord> {
  const response = await apiClient.put(`/qa/records/${id}/archive`);
  return response.data;
}

export async function restoreRecord(id: number): Promise<QARecord> {
  const response = await apiClient.put(`/qa/records/${id}/restore`);
  return response.data;
}

export async function deleteRecord(id: number): Promise<void> {
  await apiClient.delete(`/qa/records/${id}`);
}
