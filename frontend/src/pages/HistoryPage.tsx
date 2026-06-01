import {
  Button,
  Card,
  Input,
  List,
  message,
  Modal,
  Select,
  Space,
  Tag,
  Typography,
  Empty,
  Spin,
  Pagination,
} from 'antd';
import {
  SearchOutlined,
  DeleteOutlined,
  InboxOutlined,
  UndoOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getQARecords, archiveRecord, restoreRecord, deleteRecord } from '../api/qa';
import type { QARecord } from '../types';
import { formatCampusDateTime } from '../utils/dateTime';

export function HistoryPage() {
  const navigate = useNavigate();
  const [records, setRecords] = useState<QARecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [status, setStatus] = useState<'active' | 'archived'>('active');
  const [searchText, setSearchText] = useState('');
  const [timeFilter, setTimeFilter] = useState('all');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [messageApi, contextHolder] = message.useMessage();

  const pageSize = 20;

  useEffect(() => {
    loadRecords();
  }, [currentPage, status]);

  async function loadRecords() {
    setLoading(true);
    try {
      const skip = (currentPage - 1) * pageSize;
      const response = await getQARecords(status, skip, pageSize);
      setRecords(response.records);
      setTotal(response.total);
    } catch (error) {
      console.error('Failed to load records:', error);
      messageApi.error('加载历史记录失败');
    } finally {
      setLoading(false);
    }
  }

  async function handleArchive(id: number) {
    try {
      await archiveRecord(id);
      messageApi.success('已归档');
      loadRecords();
    } catch (error) {
      messageApi.error('归档失败');
    }
  }

  async function handleRestore(id: number) {
    try {
      await restoreRecord(id);
      messageApi.success('已恢复');
      loadRecords();
    } catch (error) {
      messageApi.error('恢复失败');
    }
  }

  function handleDelete(id: number) {
    Modal.confirm({
      title: '确认删除',
      content: '删除后无法恢复，确定要删除这条记录吗？',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteRecord(id);
          messageApi.success('已删除');
          loadRecords();
        } catch (error) {
          messageApi.error('删除失败');
        }
      },
    });
  }

  function handleBatchDelete() {
    if (selectedIds.length === 0) {
      messageApi.warning('请先选择要删除的记录');
      return;
    }

    Modal.confirm({
      title: '批量删除',
      content: `确定要删除选中的 ${selectedIds.length} 条记录吗？删除后无法恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await Promise.all(selectedIds.map(id => deleteRecord(id)));
          messageApi.success(`已删除 ${selectedIds.length} 条记录`);
          setSelectedIds([]);
          loadRecords();
        } catch (error) {
          messageApi.error('批量删除失败');
        }
      },
    });
  }

  function toggleSelect(id: number) {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  }

  function toggleSelectAll() {
    if (selectedIds.length === records.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(records.map(r => r.id));
    }
  }

  const filteredRecords = searchText
    ? records.filter(r =>
        r.question.toLowerCase().includes(searchText.toLowerCase()) ||
        r.answer.toLowerCase().includes(searchText.toLowerCase())
      )
    : records;

  return (
    <div className="history-page">
      {contextHolder}
      <div className="history-page-header">
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
            返回
          </Button>
          <Typography.Title level={2} style={{ margin: 0 }}>
            历史记录
          </Typography.Title>
        </Space>
        <Typography.Text type="secondary">
          共 {total} 条{status === 'archived' ? '归档' : ''}记录
        </Typography.Text>
      </div>

      <Card className="history-page-content">
        <div className="history-page-toolbar">
          <Space wrap>
            <Input
              placeholder="搜索问题或回答..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              allowClear
              style={{ width: 300 }}
            />
            <Select
              value={timeFilter}
              onChange={setTimeFilter}
              style={{ width: 120 }}
              options={[
                { value: 'all', label: '全部时间' },
                { value: 'today', label: '今天' },
                { value: 'week', label: '最近 7 天' },
                { value: 'month', label: '最近 30 天' },
              ]}
            />
            <Button
              type={status === 'archived' ? 'primary' : 'default'}
              icon={<InboxOutlined />}
              onClick={() => setStatus(status === 'active' ? 'archived' : 'active')}
            >
              {status === 'active' ? '归档区' : '返回活跃'}
            </Button>
          </Space>
          <Space>
            {status === 'active' && (
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={handleBatchDelete}
                disabled={selectedIds.length === 0}
              >
                批量删除 {selectedIds.length > 0 && `(${selectedIds.length})`}
              </Button>
            )}
          </Space>
        </div>

        {loading ? (
          <div className="history-page-loading">
            <Spin size="large" />
          </div>
        ) : filteredRecords.length === 0 ? (
          <Empty description="暂无记录" style={{ margin: '40px 0' }} />
        ) : (
          <>
            {status === 'active' && (
              <div className="history-page-select-all">
                <Button size="small" onClick={toggleSelectAll}>
                  {selectedIds.length === records.length ? '取消全选' : '全选'}
                </Button>
              </div>
            )}
            <List
              dataSource={filteredRecords}
              renderItem={record => (
                <div className={`history-record-card ${selectedIds.includes(record.id) ? 'selected' : ''}`}>
                  {status === 'active' && (
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(record.id)}
                      onChange={() => toggleSelect(record.id)}
                      className="history-record-checkbox"
                    />
                  )}
                  <div className="history-record-content">
                    <div className="history-record-question-large">
                      {record.question}
                    </div>
                    <div className="history-record-answer">
                      {record.answer.length > 200
                        ? record.answer.substring(0, 200) + '...'
                        : record.answer}
                    </div>
                    <div className="history-record-footer">
                      <Space>
                        <Tag color="green">{record.model_provider}</Tag>
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          {formatCampusDateTime(record.created_at)}
                        </Typography.Text>
                      </Space>
                      <Space>
                        <Button
                          size="small"
                          onClick={() => navigate('/', { state: { record } })}
                        >
                          查看
                        </Button>
                        {status === 'active' ? (
                          <>
                            <Button
                              size="small"
                              icon={<InboxOutlined />}
                              onClick={() => handleArchive(record.id)}
                            >
                              归档
                            </Button>
                            <Button
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                              onClick={() => handleDelete(record.id)}
                            >
                              删除
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button
                              size="small"
                              icon={<UndoOutlined />}
                              onClick={() => handleRestore(record.id)}
                            >
                              恢复
                            </Button>
                            <Button
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                              onClick={() => handleDelete(record.id)}
                            >
                              删除
                            </Button>
                          </>
                        )}
                      </Space>
                    </div>
                  </div>
                </div>
              )}
            />
            <div className="history-page-pagination">
              <Pagination
                current={currentPage}
                total={total}
                pageSize={pageSize}
                onChange={page => setCurrentPage(page)}
                showTotal={total => `共 ${total} 条`}
              />
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
