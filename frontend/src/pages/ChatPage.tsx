import { Alert, Button, Card, Space, Statistic, Typography, message } from 'antd';
import { useMemo, useRef, useState } from 'react';
import { askQuestionStream, getConversationSessionRecords } from '../api/qa';
import { submitFeedback } from '../api/feedback';
import { ChatBox } from '../components/ChatBox';
import { MessageList, type ChatMessage } from '../components/MessageList';
import { HistorySidebar } from '../components/HistorySidebar';
import { useNavigate } from 'react-router-dom';
import type { ConversationSession } from '../types';

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<number | undefined>();
  const [conversationSummary, setConversationSummary] = useState('');
  const [messageApi, contextHolder] = message.useMessage();
  const assistantIdRef = useRef<string>('');
  const navigate = useNavigate();

  const answerCount = useMemo(
    () => messages.filter((item) => item.role === 'assistant' && item.qaRecordId && !item.streaming).length,
    [messages],
  );

  async function handleSend(question: string) {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
    };
    const assistantId = crypto.randomUUID();
    assistantIdRef.current = assistantId;
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      streaming: true,
    };
    setMessages((current) => [...current, userMessage, assistantMessage]);
    setLoading(true);

    await askQuestionStream(question, {
      onMetadata(data) {
        setSessionId(data.session_id);
        setConversationSummary(data.conversation_summary);
        setMessages((current) =>
          current.map((m) =>
            m.id === assistantId
              ? { ...m, context: data.retrieved_context, modelProvider: data.model_provider }
              : m,
          ),
        );
      },
      onChunk(content) {
        setMessages((current) =>
          current.map((m) =>
            m.id === assistantId ? { ...m, content: m.content + content } : m,
          ),
        );
      },
      onDone(data) {
        setSessionId(data.session_id);
        setConversationSummary(data.conversation_summary);
        setMessages((current) =>
          current.map((m) =>
            m.id === assistantId
              ? { ...m, qaRecordId: data.qa_record_id, streaming: false }
              : m,
          ),
        );
        setLoading(false);
      },
      onError(error) {
        setMessages((current) =>
          current.map((m) =>
            m.id === assistantId ? { ...m, content: error.message || '模型或 Embedding 服务不可用。', streaming: false } : m,
          ),
        );
        messageApi.error(error.message || '问答请求失败，请确认后端服务已启动。');
        setLoading(false);
      },
    }, sessionId);
  }

  async function handleFeedback(qaRecordId: number, rating: 'like' | 'dislike') {
    await submitFeedback({ qa_record_id: qaRecordId, rating });
    setMessages((current) =>
      current.map((item) => (item.qaRecordId === qaRecordId ? { ...item, feedbackSent: true } : item)),
    );
    messageApi.success('反馈已提交');
  }

  async function handleSelectSession(session: ConversationSession) {
    try {
      const response = await getConversationSessionRecords(session.id);
      const sessionMessages = response.records.flatMap<ChatMessage>((record) => [
        {
          id: crypto.randomUUID(),
          role: 'user',
          content: record.question,
        },
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: record.answer,
          context: record.retrieved_context,
          modelProvider: record.model_provider,
          qaRecordId: record.id,
        },
      ]);
      setMessages(sessionMessages);
      setSessionId(session.id);
      setConversationSummary(session.summary);
    } catch (error) {
      console.error('Failed to load session records:', error);
      messageApi.error('加载会话失败，请稍后重试');
    }
  }

  function handleViewAll() {
    navigate('/history');
  }

  function handleNewSession() {
    setMessages([]);
    setSessionId(undefined);
    setConversationSummary('');
  }

  function handleSessionRemoved(removedSessionId: number) {
    if (sessionId !== removedSessionId) {
      return;
    }
    handleNewSession();
  }

  return (
    <div className="page-grid chat-page">
      {contextHolder}
      <HistorySidebar
        onSelectSession={(session) => void handleSelectSession(session)}
        onViewAll={handleViewAll}
        onSessionRemoved={handleSessionRemoved}
        currentSessionId={sessionId}
      />
      <section className="workspace-panel">
        <Space direction="vertical" size={18} className="full-width">
          <div className="page-heading">
            <div>
              <Typography.Title level={2}>高校校园服务智能问答系统</Typography.Title>
              <Typography.Text type="secondary">先检索校园知识库，再生成可追溯回答。</Typography.Text>
            </div>
            <Space>
              {sessionId && <Statistic title="当前会话" value={sessionId} prefix="#" />}
              <Statistic title="本轮回答" value={answerCount} suffix="条" />
              <Button onClick={handleNewSession} disabled={loading}>
                新会话
              </Button>
            </Space>
          </div>
          <Alert
            showIcon
            type="info"
            message="试试：校园卡怎么挂失？图书馆开放时间是什么？宿舍报修在哪里提交？"
          />
          <MessageList messages={messages} onFeedback={handleFeedback} />
          <ChatBox loading={loading} onSend={handleSend} />
        </Space>
      </section>
      <aside className="side-note">
        <Card title="回答规则">
          <Space direction="vertical">
            <Typography.Text>优先依据知识库回答。</Typography.Text>
            <Typography.Text>缺少依据时明确说明，不编造。</Typography.Text>
            <Typography.Text>地点、时间、电话、网址按来源原样引用。</Typography.Text>
            {conversationSummary && (
              <Typography.Text type="secondary">
                会话摘要：{conversationSummary}
              </Typography.Text>
            )}
          </Space>
        </Card>
      </aside>
    </div>
  );
}
