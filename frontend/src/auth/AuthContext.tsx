import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, setUnauthorizedHandler, tokens } from "../api/client";
import type { Branch, Me } from "../api/types";

const BRANCH_KEY = "modiq.branch";

interface AuthState {
  me: Me | null;
  loading: boolean;
  branch: Branch | null;
  isManager: boolean;
  setBranchId: (id: number) => void;
  login: (phone: string, password: string) => Promise<void>;
  register: (data: { phone: string; password: string; full_name: string; business_name: string }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [branchId, setBranchIdState] = useState<number | null>(() => Number(localStorage.getItem(BRANCH_KEY)) || null);

  const logout = useCallback(() => {
    tokens.clear();
    setMe(null);
  }, []);

  const loadMe = useCallback(async () => {
    if (!tokens.access) {
      setLoading(false);
      return;
    }
    try {
      setMe(await api<Me>("/auth/me/"));
    } catch {
      setMe(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => setMe(null));
    void loadMe();
  }, [loadMe]);

  const login = useCallback(async (phone: string, password: string) => {
    const t = await api<{ access: string; refresh: string }>("/auth/login/", {
      method: "POST", body: { phone, password }, auth: false,
    });
    tokens.set(t.access, t.refresh);
    setMe(await api<Me>("/auth/me/"));
  }, []);

  const register = useCallback(async (data: { phone: string; password: string; full_name: string; business_name: string }) => {
    await api("/auth/register/", { method: "POST", body: data, auth: false });
    await login(data.phone, data.password);
  }, [login]);

  const setBranchId = useCallback((id: number) => {
    localStorage.setItem(BRANCH_KEY, String(id));
    setBranchIdState(id);
  }, []);

  const value = useMemo<AuthState>(() => {
    const branches = me?.branches ?? [];
    const branch = branches.find((b) => b.id === branchId) ?? branches[0] ?? null;
    return {
      me, loading, branch, setBranchId, login, register, logout,
      isManager: me?.role === "owner" || me?.role === "manager",
    };
  }, [me, loading, branchId, setBranchId, login, register, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth AuthProvider ichida ishlatilishi kerak");
  return ctx;
}
