import { Input, List, Tag, Typography, Button, Spin, Empty, Popconfirm, message } from 'antd';
import { SearchOutlined, HistoryOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { archiveRecord, deleteRecord, getQARecords } from '../api/qa';
import type { QARecord } from '../types';

interface HistorySidebarProps {
  onSelectRecord: (record: QARecord) => void;
  onViewAll: () => void;
  currentRecordId?: number;
}

export function HistorySidebar({ onSelectRecord, onViewAll, currentRecordId }: HistorySidebarProps) {
  const [records, setRecords] = useState<QARecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionRecordId, setActionRecordId] = useState<number | null>(null);
  const [searchText, setSearchText] = useState('');
  const [messageApi, contextHolder] = message.useMessage();

  useEffect(() => {
    loadRecords();
  }, []);

  async function loadRecords() {
    setLoading(true);
    try {
      const response = await getQARecords('active', 0, 20);
      setRecords(response.records);
    } catch (error) {
      console.error('Failed to load records:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleArchive(recordId: number) {
    setActionRecordId(recordId);
    try {
      await archiveRecord(recordId);
      setRecords(current => current.filter(record => record.id !== recordId));
      messageApi.success('已归档');
    } catch (error) {
      console.error('Failed to archive record:', error);
      messageApi.error('归档失败，请稍后重试');
    } finally {
      setActionRecordId(null);
    }
  }

  async function handleDelete(recordId: number) {
    setActionRecordId(recordId);
    try {
      await deleteRecord(recordId);
      setRecords(current => current.filter(record => record.id !== recordId));
      messageApi.success('已删除');
    } catch (error) {
      console.error('Failed to delete record:', error);
      messageApi.error('删除失败，请稍后重试');
    } finally {
      setActionRecordId(null);
    }
  }

  const filteredRecords = searchText
    ? records.filter(r =>
        r.question.toLowerCase().includes(searchText.toLowerCase()) ||
        r.answer.toLowerCase().includes(searchText.toLowerCase())
      )
    : records;

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
        ) : filteredRecords.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无历史记录"
            style={{ margin: '20px 0' }}
          />
        ) : (
          <List
            dataSource={filteredRecords}
            size="small"
            renderItem={record => (
              <div
                className={`history-record-item ${
                  record.id === currentRecordId ? 'active' : ''
                }`}
                onClick={() => onSelectRecord(record)}
              >
                <div className="history-record-question">
                  {record.question}
                </div>
                <div className="history-record-meta">
                  <Tag color="green" style={{ margin: 0 }}>
                    {record.model_provider}
                  </Tag>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {new Date(record.created_at).toLocaleDateString('zh-CN', {
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </Typography.Text>
                </div>
                <div className="history-record-actions" onClick={event => event.stopPropagation()}>
                  <Button
                    type="link"
                    size="small"
                    loading={actionRecordId === record.id}
                    onClick={() => void handleArchive(record.id)}
                  >
                    归档
                  </Button>
                  <Popconfirm
                    title="删除这条历史记录？"
                    description="删除后不可恢复。"
                    okText="删除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                    onConfirm={() => void handleDelete(record.id)}
                  >
                    <Button danger type="link" size="small" loading={actionRecordId === record.id}>
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
