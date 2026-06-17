import { Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { FileText, History, LayoutDashboard, LogOut, Sparkles, TableProperties, Users } from "lucide-react";

import { useAuth } from "./context/AuthContext";
import Dashboard from "./pages/Dashboard";
import GenerateResume from "./pages/GenerateResume";
import HistoryPage from "./pages/History";
import JobDescriptionCreate from "./pages/JobDescriptionCreate";
import Login from "./pages/Login";
import PromptCreate from "./pages/PromptCreate";
import ResumeCreate from "./pages/ResumeCreate";
import ResumeResult from "./pages/ResumeResult";
import UserManagement from "./pages/UserManagement";
import WorkHistory from "./pages/WorkHistory";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="center-screen">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function Shell({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Sparkles size={22} />
          <span>ATS Resume</span>
        </div>
        <nav>
          <NavLink to="/"><LayoutDashboard size={18} />Dashboard</NavLink>
          <NavLink to="/resume"><FileText size={18} />Resume</NavLink>
          <NavLink to="/job"><FileText size={18} />Job</NavLink>
          <NavLink to="/prompt"><FileText size={18} />Prompt</NavLink>
          <NavLink to="/generate"><Sparkles size={18} />Generate</NavLink>
          <NavLink to="/work-history"><TableProperties size={18} />Work History</NavLink>
          <NavLink to="/history"><History size={18} />History</NavLink>
          {user?.is_staff && <NavLink to="/users"><Users size={18} />Users</NavLink>}
        </nav>
        <button
          className="ghost-button"
          type="button"
          onClick={async () => {
            await logout();
            navigate("/login");
          }}
          title="Log out"
        >
          <LogOut size={18} /> {user?.username}
        </button>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <Protected>
            <Shell>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/resume" element={<ResumeCreate />} />
                <Route path="/job" element={<JobDescriptionCreate />} />
                <Route path="/prompt" element={<PromptCreate />} />
                <Route path="/generate" element={<GenerateResume />} />
                <Route path="/work-history" element={<WorkHistory />} />
                <Route path="/result/:id" element={<ResumeResult />} />
                <Route path="/history" element={<HistoryPage />} />
                <Route path="/users" element={userRoute(<UserManagement />)} />
              </Routes>
            </Shell>
          </Protected>
        }
      />
    </Routes>
  );
}

function userRoute(element) {
  return <AdminOnly>{element}</AdminOnly>;
}

function AdminOnly({ children }) {
  const { user } = useAuth();
  if (!user?.is_staff) return <Navigate to="/" replace />;
  return children;
}
