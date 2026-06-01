import { Button, Popconfirm, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { KnowledgeItem } from '../types';

interface KnowledgeTableProps {
  data: KnowledgeItem[];
  loading: boolean;
  onEdit: (item: KnowledgeItem) => void;
  onDelete: (id: number) => Promise<void>;
}

export function KnowledgeTable({ data, loading, onEdit, onDelete }: KnowledgeTableProps) {
  const columns: ColumnsType<KnowledgeItem> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 220,
      render: (title: string, record) => (
        <Space direction="vertical" size={2}>
          <Typography.Text strong>{title}</Typography.Text>
          <Typography.Text type="secondary">{record.source}</Typography.Text>
        </Space>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category: string) => <Tag color="green">{category}</Tag>,
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      render: (content: string) => (
        <Typography.Paragraph className="table-content" ellipsis={{ rows: 2, expandable: true }}>
          {content}
        </Typography.Paragraph>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => onEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除该知识条目？" onConfirm={() => void onDelete(record.id)}>
            <Button size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Table
      rowKey="id"
      columns={columns}
      dataSource={data}
      loading={loading}
      pagination={{ pageSize: 8 }}
    />
  );
}

