import { Alert, Card, Space, Statistic, Typography, message } from 'antd';
import { useMemo, useRef, useState } from 'react';
import { askQuestionStream } from '../api/qa';
import { submitFeedback } from '../api/feedback';
import { ChatBox } from '../components/ChatBox';
import { MessageList, type ChatMessage } from '../components/MessageList';

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();
  const assistantIdRef = useRef<string>('');

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
            m.id === assistantId ? { ...m, streaming: false } : m,
          ),
        );
        messageApi.error(error.message || '问答请求失败，请确认后端服务已启动。');
        setLoading(false);
      },
    });
  }

  async function handleFeedback(qaRecordId: number, rating: 'like' | 'dislike') {
    await submitFeedback({ qa_record_id: qaRecordId, rating });
    setMessages((current) =>
      current.map((item) => (item.qaRecordId === qaRecordId ? { ...item, feedbackSent: true } : item)),
    );
    messageApi.success('反馈已提交');
  }

  return (
    <div className="page-grid chat-page">
      {contextHolder}
      <section className="workspace-panel">
        <Space direction="vertical" size={18} className="full-width">
          <div className="page-heading">
            <div>
              <Typography.Title level={2}>高校校园服务智能问答系统</Typography.Title>
              <Typography.Text type="secondary">先检索校园知识库，再生成可追溯回答。</Typography.Text>
            </div>
            <Statistic title="本轮回答" value={answerCount} suffix="条" />
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
          </Space>
        </Card>
      </aside>
    </div>
  );
}
