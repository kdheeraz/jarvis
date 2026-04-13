import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ChatPage } from './pages/ChatPage';
import { LoginPage } from './pages/LoginPage';
import { AdminLayout } from './components/layout/AdminLayout';
import { DashboardPage } from './pages/admin/DashboardPage';
import { ConfigPage } from './pages/admin/ConfigPage';
import { ToolsPage } from './pages/admin/ToolsPage';
import { RagPage } from './pages/admin/RagPage';
import { UsersPage } from './pages/admin/UsersPage';
import { ConversationsPage } from './pages/admin/ConversationsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Chat UI */}
        <Route path="/" element={<ChatPage />} />

        {/* Auth */}
        <Route path="/login" element={<LoginPage />} />

        {/* Admin Panel */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="config" element={<ConfigPage />} />
          <Route path="tools" element={<ToolsPage />} />
          <Route path="rag" element={<RagPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="conversations" element={<ConversationsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
