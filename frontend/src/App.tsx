import { ConfigProvider, Layout, Menu, Typography, Button, Spin } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useEffect, useState } from 'react';
import { BrowserRouter, Route, Routes, useLocation, useNavigate, Navigate } from 'react-router-dom';
import { getMe } from './api/auth';
import { ChatPage } from './pages/ChatPage';
import { FeedbackPage } from './pages/FeedbackPage';
import { HistoryPage } from './pages/HistoryPage';
import { KnowledgePage } from './pages/KnowledgePage';
import { LoginPage } from './pages/LoginPage';
import type { User } from './types';

const { Sider, Content } = Layout;

// 受保护的路由组件
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token');

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      setLoading(true);
      getMe()
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('token');
          setUser(null);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, [location.pathname]);

  function handleLogout() {
    localStorage.removeItem('token');
    setUser(null);
    navigate('/login');
  }

  // 登录页面不需要认证
  if (location.pathname === '/login') {
    // 如果已登录，跳转到首页
    if (localStorage.getItem('token') && user) {
      return <Navigate to="/" replace />;
    }
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    );
  }

  // 未登录时跳转到登录页面
  if (!loading && !localStorage.getItem('token')) {
    return <Navigate to="/login" replace />;
  }

  // 加载中显示 loading
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <Layout className="app-shell">
      <Sider className="app-sidebar" width={256}>
        <div className="brand">
          <div className="brand-copy">
            <Typography.Title level={4}>高校校园服务智能问答系统</Typography.Title>
            <Typography.Text>Campus Service RAG Assistant</Typography.Text>
          </div>
        </div>
        <Menu
          className="main-nav"
          mode="inline"
          selectedKeys={[location.pathname]}
          onClick={({ key }) => navigate(key)}
          items={[
            { key: '/', label: '智能问答' },
            { key: '/knowledge', label: '知识库' },
            { key: '/history', label: '历史' },
            { key: '/feedback', label: '反馈' },
          ]}
        />
        <div className="user-info">
          <Typography.Text type="secondary">当前用户</Typography.Text>
          <Typography.Text strong>{user ? user.nickname || user.username : '加载中...'}</Typography.Text>
          <Button block size="small" onClick={handleLogout}>
            登出
          </Button>
        </div>
      </Sider>
      <Content className="app-content">
        <Routes>
          <Route path="/" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
          <Route path="/knowledge" element={<ProtectedRoute><KnowledgePage /></ProtectedRoute>} />
          <Route path="/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
          <Route path="/feedback" element={<ProtectedRoute><FeedbackPage /></ProtectedRoute>} />
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
