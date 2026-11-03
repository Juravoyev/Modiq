import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { Loading } from "./components/ui";
import { BranchesPage } from "./pages/BranchesPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DiscountsPage } from "./pages/DiscountsPage";
import { InsightsPage } from "./pages/InsightsPage";
import { LoginPage } from "./pages/LoginPage";
import { MorePage } from "./pages/MorePage";
import { PosPage } from "./pages/PosPage";
import { ProductEditPage } from "./pages/ProductEditPage";
import { ProductFormPage } from "./pages/ProductFormPage";
import { ProductsPage } from "./pages/ProductsPage";
import { ReceiptsPage } from "./pages/ReceiptsPage";
import { ReportsPage } from "./pages/ReportsPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ReturnsPage } from "./pages/ReturnsPage";
import { SalesPage } from "./pages/SalesPage";
import { SettingsPage } from "./pages/SettingsPage";
import { StaffPage } from "./pages/StaffPage";
import { StockCountPage } from "./pages/StockCountPage";
import { StockPage } from "./pages/StockPage";
import { TransfersPage } from "./pages/TransfersPage";

/** Bosh sahifa: menejer/egasi dashboardni, sotuvchi kassani ko'radi. */
function Home() {
  const { isManager } = useAuth();
  return <Navigate to={isManager ? "/dashboard" : "/pos"} replace />;
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <Loading />;
  return me ? <>{children}</> : <Navigate to="/login" replace />;
}

/** Menejer/egasi sahifalari: sotuvchi kassaga qaytariladi (server ham baribir ruxsat bermaydi). */
function ManagerOnly({ children }: { children: ReactNode }) {
  const { isManager } = useAuth();
  return isManager ? <>{children}</> : <Navigate to="/pos" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<RequireAuth><Layout /></RequireAuth>}>
            <Route index element={<Home />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="pos" element={<PosPage />} />
            <Route path="insights" element={<InsightsPage />} />
            <Route path="products" element={<ProductsPage />} />
            <Route path="products/new" element={<ManagerOnly><ProductFormPage /></ManagerOnly>} />
            <Route path="products/:id/edit" element={<ManagerOnly><ProductEditPage /></ManagerOnly>} />
            <Route path="receipts" element={<ManagerOnly><ReceiptsPage /></ManagerOnly>} />
            <Route path="transfers" element={<ManagerOnly><TransfersPage /></ManagerOnly>} />
            <Route path="counts" element={<StockCountPage />} />
            <Route path="staff" element={<ManagerOnly><StaffPage /></ManagerOnly>} />
            <Route path="branches" element={<ManagerOnly><BranchesPage /></ManagerOnly>} />
            <Route path="settings" element={<ManagerOnly><SettingsPage /></ManagerOnly>} />
            <Route path="more" element={<MorePage />} />
            <Route path="stock" element={<StockPage />} />
            <Route path="sales" element={<SalesPage />} />
            <Route path="returns" element={<ReturnsPage />} />
            <Route path="discounts" element={<ManagerOnly><DiscountsPage /></ManagerOnly>} />
            <Route path="reports" element={<ManagerOnly><ReportsPage /></ManagerOnly>} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
