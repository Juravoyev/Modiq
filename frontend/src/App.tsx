import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { Loading } from "./components/ui";
import { LoginPage } from "./pages/LoginPage";
import { PosPage } from "./pages/PosPage";
import { ProductFormPage } from "./pages/ProductFormPage";
import { ProductsPage } from "./pages/ProductsPage";
import { ReceiptsPage } from "./pages/ReceiptsPage";
import { RegisterPage } from "./pages/RegisterPage";
import { SalesPage } from "./pages/SalesPage";
import { StockPage } from "./pages/StockPage";

function RequireManager({ children }: { children: ReactNode }) {
  const { isManager } = useAuth();
  return isManager ? <>{children}</> : <Navigate to="/" replace />;
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <Loading />;
  return me ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<RequireAuth><Layout /></RequireAuth>}>
            <Route index element={<PosPage />} />
            <Route path="products" element={<ProductsPage />} />
            <Route path="products/new" element={<RequireManager><ProductFormPage /></RequireManager>} />
            <Route path="receipts" element={<RequireManager><ReceiptsPage /></RequireManager>} />
            <Route path="stock" element={<StockPage />} />
            <Route path="sales" element={<SalesPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
