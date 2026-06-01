import { ConfigProvider, Layout, Menu, Typography, Button } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useEffect, useState } from 'react';
import { BrowserRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { getMe } from './api/auth';
import { ChatPage } from './pages/ChatPage';
import { FeedbackPage } from './pages/FeedbackPage';
import { KnowledgePage } from './pages/KnowledgePage';
import { LoginPage } from './pages/LoginPage';
import type { User } from './types';

const { Header, Content } = Layout;

function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      getMe()
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('token');
          setUser(null);
        });
    }
  }, [location.pathname]);

  function handleLogout() {
    localStorage.removeItem('token');
    setUser(null);
    navigate('/');
  }

  if (location.pathname === '/login') {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    );
  }

  return (
    <Layout className="app-shell">
      <Header className="app-header">
        <div className="brand">
          <div className="brand-mark">校</div>
          <div>
            <Typography.Title level={4}>高校校园服务智能问答系统</Typography.Title>
            <Typography.Text>Campus Service RAG Assistant</Typography.Text>
          </div>
        </div>
        <Menu
          mode="horizontal"
          selectedKeys={[location.pathname]}
          onClick={({ key }) => navigate(key)}
          items={[
            { key: '/', label: '智能问答' },
            { key: '/knowledge', label: '知识库' },
            { key: '/feedback', label: '反馈' },
          ]}
        />
        <div className="user-info">
          <Typography.Text>{user ? user.nickname || user.username : '访客模式'}</Typography.Text>
          {user ? (
            <Button size="small" onClick={handleLogout}>
              登出
            </Button>
          ) : (
            <Button size="small" onClick={() => navigate('/login')}>
              登录
            </Button>
          )}
        </div>
      </Header>
      <Content className="app-content">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/feedback" element={<FeedbackPage />} />
        </Routes>
      </Content>
    </Layout>
  );
}

export default function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#14745f',
          colorInfo: '#1f6f8b',
          borderRadius: 8,
          fontFamily: '"Noto Sans SC", "Microsoft YaHei", sans-serif',
        },
      }}
    >
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </ConfigProvider>
  );
}
