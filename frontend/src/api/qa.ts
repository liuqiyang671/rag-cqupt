import { apiClient } from './client';
import type { AskResponse, KnowledgeItem } from '../types';

export async function askQuestion(question: string): Promise<AskResponse> {
  const response = await apiClient.post<AskResponse>('/qa/ask', { question });
  return response.data;
}

export interface StreamCallbacks {
  onMetadata: (data: { retrieved_context: KnowledgeItem[]; model_provider: string }) => void;
  onChunk: (content: string) => void;
  onDone: (data: { qa_record_id: number }) => void;
  onError: (error: Error) => void;
}

export async function askQuestionStream(
  question: string,
  callbacks: StreamCallbacks,
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
      body: JSON.stringify({ question }),
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
