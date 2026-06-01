import { Button, Card, Empty, List, Space, Tag, Typography } from 'antd';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { KnowledgeItem } from '../types';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  context?: KnowledgeItem[];
  qaRecordId?: number;
  modelProvider?: string;
  feedbackSent?: boolean;
  streaming?: boolean;
}

interface MessageListProps {
  messages: ChatMessage[];
  onFeedback: (qaRecordId: number, rating: 'like' | 'dislike') => Promise<void>;
}

export function MessageList({ messages, onFeedback }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <Empty
        className="empty-state"
        description="输入一个校园服务问题，系统会先检索知识库，再生成回答。"
      />
    );
  }

  return (
    <List
      className="message-list"
      dataSource={messages}
      renderItem={(message) => (
        <List.Item className={`message-row message-row-${message.role}`}>
          <Card className={`message-card ${message.role}`}>
            <Space direction="vertical" size={12} className="message-content">
              <Space wrap>
                <Tag color={message.role === 'user' ? 'blue' : 'green'}>
                  {message.role === 'user' ? '我' : '校园问答助手'}
                </Tag>
                {message.modelProvider && <Tag>{message.modelProvider}</Tag>}
              </Space>
              {message.role === 'assistant' ? (
                <div className="message-text markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content}
                  </ReactMarkdown>
                  {message.streaming && <span className="streaming-cursor" />}
                </div>
              ) : (
                <Typography.Paragraph className="message-text">
                  {message.content}
                </Typography.Paragraph>
              )}
              {message.context && message.context.length > 0 && (
                <div className="citations">
                  <Typography.Text strong>检索来源</Typography.Text>
                  {message.context.map((item) => (
                    <div className="citation" key={item.id}>
                      <Space wrap>
                        <Tag color="cyan">{item.category}</Tag>
                        <Typography.Text strong>{item.title}</Typography.Text>
                        <Typography.Text type="secondary">{item.source}</Typography.Text>
                      </Space>
                      <Typography.Paragraph ellipsis={{ rows: 2, expandable: true }}>
                        {item.content}
                      </Typography.Paragraph>
                    </div>
                  ))}
                </div>
              )}
              {message.qaRecordId && !message.streaming && (
                <Space>
                  <Button
                    size="small"
                    disabled={message.feedbackSent}
                    onClick={() => void onFeedback(message.qaRecordId!, 'like')}
                  >
                    点赞
                  </Button>
                  <Button
                    size="small"
                    disabled={message.feedbackSent}
                    onClick={() => void onFeedback(message.qaRecordId!, 'dislike')}
                  >
                    点踩
                  </Button>
                  {message.feedbackSent && <Typography.Text type="secondary">已提交反馈</Typography.Text>}
                </Space>
              )}
            </Space>
          </Card>
        </List.Item>
      )}
    />
  );
}

