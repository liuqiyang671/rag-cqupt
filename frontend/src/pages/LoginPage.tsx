import { Button, Card, Form, Input, Tabs, Typography, message } from 'antd';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, register } from '../api/auth';
import type { LoginPayload, RegisterPayload } from '../types';

export function LoginPage() {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('login');

  async function handleLogin(values: LoginPayload) {
    setLoading(true);
    try {
      const data = await login(values);
      localStorage.setItem('token', data.access_token);
      messageApi.success('登录成功');
      navigate('/');
    } catch {
      messageApi.error('用户名或密码错误');
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(values: RegisterPayload) {
    setLoading(true);
    try {
      await register(values);
      messageApi.success('注册成功，请登录');
      setActiveTab('login');
    } catch {
      messageApi.error('注册失败，用户名可能已存在');
    } finally {
      setLoading(false);
    }
  }

  const items = [
    {
      key: 'login',
      label: '登录',
      children: (
        <Form layout="vertical" onFinish={handleLogin} autoComplete="off">
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>
      ),
    },
    {
      key: 'register',
      label: '注册',
      children: (
        <Form layout="vertical" onFinish={handleRegister} autoComplete="off">
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名至少 3 个字符' },
            ]}
          >
            <Input placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少 6 个字符' },
            ]}
          >
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Form.Item name="nickname" label="昵称">
            <Input placeholder="可选，不填则使用用户名" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              注册
            </Button>
          </Form.Item>
        </Form>
      ),
    },
  ];

  return (
    <div className="login-page">
      {contextHolder}
      <Card className="login-card">
        <Typography.Title level={3} style={{ textAlign: 'center', marginBottom: 24 }}>
          高校校园服务智能问答系统
        </Typography.Title>
        <Tabs activeKey={activeTab} onChange={setActiveTab} centered items={items} />
      </Card>
    </div>
  );
}
