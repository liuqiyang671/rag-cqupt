import { Button, Form, Input, Select, Space } from 'antd';
import type { KnowledgePayload } from '../types';

const categories = [
  '教务服务',
  '图书馆服务',
  '校园卡服务',
  '宿舍服务',
  '奖助学金',
  '就业服务',
  '医疗服务',
  '后勤报修',
  '校园网络',
];

interface KnowledgeFormProps {
  initialValues?: Partial<KnowledgePayload>;
  submitting: boolean;
  onSubmit: (payload: KnowledgePayload) => Promise<void>;
  onCancel: () => void;
}

export function KnowledgeForm({ initialValues, submitting, onSubmit, onCancel }: KnowledgeFormProps) {
  const [form] = Form.useForm<KnowledgePayload>();

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={{ source: '校内知识库', ...initialValues }}
      onFinish={(values) => void onSubmit(values)}
    >
      <Form.Item name="title" label="标题" rules={[{ required: true, message: '请输入标题' }]}>
        <Input placeholder="例如：校园卡挂失流程" />
      </Form.Item>
      <Form.Item name="category" label="分类" rules={[{ required: true, message: '请选择分类' }]}>
        <Select options={categories.map((category) => ({ label: category, value: category }))} />
      </Form.Item>
      <Form.Item name="source" label="来源" rules={[{ required: true, message: '请输入来源' }]}>
        <Input placeholder="例如：校园卡服务中心" />
      </Form.Item>
      <Form.Item name="content" label="内容" rules={[{ required: true, message: '请输入内容' }]}>
        <Input.TextArea rows={7} placeholder="输入可被问答系统引用的校内服务说明" />
      </Form.Item>
      <Space className="form-actions">
        <Button onClick={onCancel}>取消</Button>
        <Button type="primary" htmlType="submit" loading={submitting}>
          保存
        </Button>
      </Space>
    </Form>
  );
}

export { categories };

