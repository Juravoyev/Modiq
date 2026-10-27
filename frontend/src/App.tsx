import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { Loading } from "./components/ui";
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
import { SalesPage } from "./pages/SalesPage";
import { SettingsPage } from "./pages/SettingsPage";
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
            <Route path="products/new" element={<ProductFormPage />} />
            <Route path="products/:id/edit" element={<ProductEditPage />} />
            <Route path="transfers" element={<TransfersPage />} />
            <Route path="counts" element={<StockCountPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="more" element={<MorePage />} />
            <Route path="receipts" element={<ReceiptsPage />} />
            <Route path="stock" element={<StockPage />} />
            <Route path="sales" element={<SalesPage />} />
            <Route path="discounts" element={<ManagerOnly><DiscountsPage /></ManagerOnly>} />
            <Route path="reports" element={<ManagerOnly><ReportsPage /></ManagerOnly>} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
