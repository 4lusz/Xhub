import { Navigate, Route, Routes } from "react-router-dom";

import { AuthLayout } from "@/layouts/AuthLayout";
import { DashboardLayout } from "@/layouts/DashboardLayout";
import { MarketingLayout } from "@/layouts/MarketingLayout";
import { AdminRoute } from "@/routes/AdminRoute";
import { ClientOnlyRoute } from "@/routes/ClientOnlyRoute";
import { ProtectedRoute } from "@/routes/ProtectedRoute";

import { LandingPage } from "@/pages/LandingPage";
import { AboutPage } from "@/pages/AboutPage";
import { ContactPage } from "@/pages/ContactPage";
import { FaqPage } from "@/pages/FaqPage";
import { PrivacyPolicyPage } from "@/pages/PrivacyPolicyPage";
import { TermsOfUsePage } from "@/pages/TermsOfUsePage";
import { LoginPage } from "@/pages/LoginPage";
import { FirstAccessPage } from "@/pages/FirstAccessPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { AccountsPage } from "@/pages/AccountsPage";
import { PostsPage } from "@/pages/PostsPage";
import { NewPostPage } from "@/pages/NewPostPage";
import { ScheduledPage } from "@/pages/ScheduledPage";
import { ResultsPage } from "@/pages/ResultsPage";
import { AccountResultsDetailPage } from "@/pages/AccountResultsDetailPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { SettingsPage } from "@/pages/SettingsPage";
import { AdminDashboardPage } from "@/pages/AdminDashboardPage";
import { AdminUsersPage } from "@/pages/AdminUsersPage";
import { AdminPlansPage } from "@/pages/AdminPlansPage";
import { AdminAuditLogsPage } from "@/pages/AdminAuditLogsPage";
import { AdminPostsPage } from "@/pages/AdminPostsPage";
import { AdminJitterSettingsPage } from "@/pages/AdminJitterSettingsPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

function App() {
  return (
    <Routes>
      <Route element={<MarketingLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/sobre" element={<AboutPage />} />
        <Route path="/contato" element={<ContactPage />} />
        <Route path="/faq" element={<FaqPage />} />
        <Route path="/privacidade" element={<PrivacyPolicyPage />} />
        <Route path="/termos" element={<TermsOfUsePage />} />
      </Route>

      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route path="/first-access" element={<FirstAccessPage />} />

        <Route element={<DashboardLayout />}>
          <Route element={<ClientOnlyRoute />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/accounts" element={<AccountsPage />} />
            <Route path="/posts" element={<PostsPage />} />
            <Route path="/posts/new" element={<NewPostPage />} />
            <Route path="/scheduled" element={<ScheduledPage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/results/:accountId" element={<AccountResultsDetailPage />} />
          </Route>

          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/settings" element={<SettingsPage />} />

          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<AdminDashboardPage />} />
            <Route path="/admin/users" element={<AdminUsersPage />} />
            <Route path="/admin/plans" element={<AdminPlansPage />} />
            <Route path="/admin/audit-logs" element={<AdminAuditLogsPage />} />
            <Route path="/admin/posts" element={<AdminPostsPage />} />
            <Route path="/admin/jitter" element={<AdminJitterSettingsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="/404" element={<NotFoundPage />} />
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  );
}

export default App;
