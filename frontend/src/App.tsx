import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./state/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";

import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import InventoryPage from "./pages/InventoryPage";
import ProductDetailPage from "./pages/ProductDetailPage";
import SalesPage from "./pages/SalesPage";
import AllotmentsPage from "./pages/AllotmentsPage";
import PurchasingPage from "./pages/PurchasingPage";
import AgingPage from "./pages/AgingPage";
import DeadlinesPage from "./pages/DeadlinesPage";
import ForecastingPage from "./pages/ForecastingPage";
import RecommendationsPage from "./pages/RecommendationsPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import ImportCenterPage from "./pages/ImportCenterPage";
import ReportsPage from "./pages/ReportsPage";
import DataQualityPage from "./pages/DataQualityPage";
import SettingsPage from "./pages/SettingsPage";
import UsersPage from "./pages/UsersPage";
import AuditLogsPage from "./pages/AuditLogsPage";
import ProfilePage from "./pages/ProfilePage";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<DashboardPage />} />
            <Route path="/inventory" element={<InventoryPage />} />
            <Route path="/inventory/:variantId" element={<ProductDetailPage />} />
            <Route path="/sales" element={<SalesPage />} />
            <Route path="/allotments" element={<AllotmentsPage />} />
            <Route path="/purchasing" element={<PurchasingPage />} />
            <Route path="/aging" element={<AgingPage />} />
            <Route path="/deadlines" element={<DeadlinesPage />} />
            <Route path="/forecasting" element={<ForecastingPage />} />
            <Route path="/recommendations" element={<RecommendationsPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/imports" element={<ImportCenterPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/data-quality" element={<DataQualityPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/users" element={<UsersPage />} />
            <Route path="/audit-logs" element={<AuditLogsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
