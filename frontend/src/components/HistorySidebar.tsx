import { Input, List, Tag, Typography, Button, Spin, Empty, Popconfirm, message } from 'antd';
import { SearchOutlined, HistoryOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { archiveSession, deleteSession, getConversationSessions } from '../api/qa';
import type { ConversationSession } from '../types';

interface HistorySidebarProps {
  onSelectSession: (session: ConversationSession) => void;
  onViewAll: () => void;
  onSessionRemoved?: (sessionId: number) => void;
  currentSessionId?: number;
}

export function HistorySidebar({
  onSelectSession,
  onViewAll,
  onSessionRemoved,
  currentSessionId,
}: HistorySidebarProps) {
  const [sessions, setSessions] = useState<ConversationSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionSessionId, setActionSessionId] = useState<number | null>(null);
  const [searchText, setSearchText] = useState('');
  const [messageApi, contextHolder] = message.useMessage();

  useEffect(() => {
    loadRecords();
  }, []);

  async function loadRecords() {
    setLoading(true);
    try {
      const response = await getConversationSessions('active', 0, 20);
      setSessions(response.sessions);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleArchive(sessionId: number) {
    setActionSessionId(sessionId);
    try {
      await archiveSession(sessionId);
      setSessions(current => current.filter(session => session.id !== sessionId));
      onSessionRemoved?.(sessionId);
      messageApi.success('已归档');
    } catch (error) {
      console.error('Failed to archive session:', error);
      messageApi.error('归档失败，请稍后重试');
    } finally {
      setActionSessionId(null);
    }
  }

  async function handleDelete(sessionId: number) {
    setActionSessionId(sessionId);
    try {
      await deleteSession(sessionId);
      setSessions(current => current.filter(session => session.id !== sessionId));
      onSessionRemoved?.(sessionId);
      messageApi.success('已删除');
    } catch (error) {
      console.error('Failed to delete session:', error);
      messageApi.error('删除失败，请稍后重试');
    } finally {
      setActionSessionId(null);
    }
  }

  const filteredSessions = searchText
    ? sessions.filter(session =>
        session.title.toLowerCase().includes(searchText.toLowerCase()) ||
        (session.latest_question || '').toLowerCase().includes(searchText.toLowerCase()) ||
        (session.latest_answer || '').toLowerCase().includes(searchText.toLowerCase()) ||
        session.summary.toLowerCase().includes(searchText.toLowerCase())
      )
    : sessions;

  return (
    <div className="history-sidebar">
      {contextHolder}
      <div className="history-sidebar-header">
        <Typography.Title level={5} style={{ margin: 0 }}>
          <HistoryOutlined /> 历史记录
        </Typography.Title>
        <Button type="link" size="small" onClick={onViewAll}>
          查看全部
        </Button>
      </div>

      <Input
        placeholder="搜索历史..."
        prefix={<SearchOutlined />}
        value={searchText}
        onChange={e => setSearchText(e.target.value)}
        allowClear
        size="small"
        style={{ marginBottom: 12 }}
      />

      <div className="history-sidebar-list">
        {loading ? (
          <div className="history-sidebar-loading">
            <Spin size="small" />
          </div>
        ) : filteredSessions.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无历史记录"
            style={{ margin: '20px 0' }}
          />
        ) : (
          <List
            dataSource={filteredSessions}
            size="small"
            renderItem={session => (
              <div
                className={`history-record-item ${
                  session.id === currentSessionId ? 'active' : ''
                }`}
                onClick={() => onSelectSession(session)}
              >
                <div className="history-record-question">
                  {session.title}
                </div>
                <div className="history-record-meta">
                  <Tag color="green" style={{ margin: 0 }}>
                    {session.latest_model_provider || 'session'}
                  </Tag>
                  <Tag color="blue" style={{ margin: 0 }}>
                    {session.round_count} 轮
                  </Tag>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {new Date(session.latest_record_created_at || session.updated_at).toLocaleDateString('zh-CN', {
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </Typography.Text>
                </div>
                {session.latest_question && (
                  <Typography.Text className="history-record-latest" type="secondary">
                    {session.latest_question}
                  </Typography.Text>
                )}
                <div className="history-record-actions" onClick={event => event.stopPropagation()}>
                  <Button
                    type="link"
                    size="small"
                    loading={actionSessionId === session.id}
                    onClick={() => void handleArchive(session.id)}
                  >
                    归档
                  </Button>
                  <Popconfirm
                    title="删除这条历史记录？"
                    description="删除后不可恢复。"
                    okText="删除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                    onConfirm={() => void handleDelete(session.id)}
                  >
                    <Button danger type="link" size="small" loading={actionSessionId === session.id}>
                      删除
                    </Button>
                  </Popconfirm>
                </div>
              </div>
            )}
          />
        )}
      </div>
    </div>
  );
}
