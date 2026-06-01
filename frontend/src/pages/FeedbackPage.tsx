import { Card, List, Space, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { fetchFeedback } from '../api/feedback';
import type { FeedbackItem } from '../types';

export function FeedbackPage() {
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  useEffect(() => {
    async function loadFeedback() {
      setLoading(true);
      try {
        setItems(await fetchFeedback());
      } catch (error) {
        messageApi.error('反馈列表加载失败，请确认后端服务已启动。');
      } finally {
        setLoading(false);
      }
    }
    void loadFeedback();
  }, [messageApi]);

  return (
    <section className="workspace-panel">
      {contextHolder}
      <Space direction="vertical" size={18} className="full-width">
        <div className="page-heading">
          <div>
            <Typography.Title level={2}>用户反馈</Typography.Title>
            <Typography.Text type="secondary">查看问答页面提交的点赞、点踩和文字反馈。</Typography.Text>
          </div>
        </div>
        <Card>
          <List
            loading={loading}
            dataSource={items}
            locale={{ emptyText: '暂无反馈记录' }}
            renderItem={(item) => (
              <List.Item>
                <Space direction="vertical" size={4}>
                  <Space wrap>
                    <Tag color={item.rating === 'like' ? 'green' : 'red'}>
                      {item.rating === 'like' ? '点赞' : '点踩'}
                    </Tag>
                    <Typography.Text>问答记录 #{item.qa_record_id}</Typography.Text>
                    <Typography.Text type="secondary">{new Date(item.created_at).toLocaleString()}</Typography.Text>
                  </Space>
                  <Typography.Text>{item.comment || '未填写文字反馈'}</Typography.Text>
                </Space>
              </List.Item>
            )}
          />
        </Card>
      </Space>
    </section>
  );
}

