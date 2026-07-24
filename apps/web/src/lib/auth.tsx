"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  active_organization_id: string | null;
  is_email_verified: boolean;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
};

type AuthState = {
  user: AuthUser | null;
  organizations: Organization[];
  accessToken: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    full_name: string;
    organization_name: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
  switchOrganization: (organizationId: string) => Promise<void>;
  authFetch: (path: string, init?: RequestInit) => Promise<Response>;
};

const AuthContext = createContext<AuthState | null>(null);

const STORAGE_KEY = "atlas.auth.v1";

type StoredAuth = {
  accessToken: string;
  refreshToken: string;
};

function loadStored(): StoredAuth | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredAuth;
  } catch {
    return null;
  }
}

function saveStored(value: StoredAuth | null) {
  if (typeof window === "undefined") return;
  if (!value) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const persistTokens = useCallback((access: string, refresh: string) => {
    setAccessToken(access);
    setRefreshToken(refresh);
    saveStored({ accessToken: access, refreshToken: refresh });
  }, []);

  const authFetch = useCallback(
    async (path: string, init: RequestInit = {}) => {
      const headers = new Headers(init.headers || {});
      if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
      if (!headers.has("Content-Type") && init.body) {
        headers.set("Content-Type", "application/json");
      }
      let response = await fetch(`${API_URL}${path}`, { ...init, headers });
      if (response.status === 401 && refreshToken) {
        const refreshed = await fetch(`${API_URL}/v1/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (refreshed.ok) {
          const data = (await refreshed.json()) as {
            access_token: string;
            refresh_token: string;
          };
          persistTokens(data.access_token, data.refresh_token);
          headers.set("Authorization", `Bearer ${data.access_token}`);
          response = await fetch(`${API_URL}${path}`, { ...init, headers });
        }
      }
      return response;
    },
    [accessToken, refreshToken, persistTokens],
  );

  const refreshMe = useCallback(async () => {
    if (!accessToken) {
      setUser(null);
      setOrganizations([]);
      return;
    }
    const meRes = await authFetch("/v1/auth/me");
    if (!meRes.ok) {
      setUser(null);
      return;
    }
    setUser((await meRes.json()) as AuthUser);
    const orgRes = await authFetch("/v1/organizations");
    if (orgRes.ok) {
      setOrganizations((await orgRes.json()) as Organization[]);
    }
  }, [accessToken, authFetch]);

  useEffect(() => {
    const stored = loadStored();
    if (stored) {
      setAccessToken(stored.accessToken);
      setRefreshToken(stored.refreshToken);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!loading && accessToken) {
      void refreshMe();
    }
  }, [loading, accessToken, refreshMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await fetch(`${API_URL}/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Login failed" }));
        throw new Error(err.detail || "Login failed");
      }
      const data = await res.json();
      persistTokens(data.access_token, data.refresh_token);
    },
    [persistTokens],
  );

  const register = useCallback(
    async (payload: {
      email: string;
      password: string;
      full_name: string;
      organization_name: string;
    }) => {
      const res = await fetch(`${API_URL}/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Registration failed" }));
        throw new Error(err.detail || "Registration failed");
      }
      const data = await res.json();
      persistTokens(data.access_token, data.refresh_token);
    },
    [persistTokens],
  );

  const logout = useCallback(async () => {
    if (accessToken) {
      await authFetch("/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    }
    setUser(null);
    setOrganizations([]);
    setAccessToken(null);
    setRefreshToken(null);
    saveStored(null);
  }, [accessToken, authFetch]);

  const switchOrganization = useCallback(
    async (organizationId: string) => {
      const res = await authFetch("/v1/organizations/switch", {
        method: "POST",
        body: JSON.stringify({ organization_id: organizationId }),
      });
      if (!res.ok) throw new Error("Unable to switch organization");
      await refreshMe();
    },
    [authFetch, refreshMe],
  );

  const value = useMemo(
    () => ({
      user,
      organizations,
      accessToken,
      loading,
      login,
      register,
      logout,
      refreshMe,
      switchOrganization,
      authFetch,
    }),
    [
      user,
      organizations,
      accessToken,
      loading,
      login,
      register,
      logout,
      refreshMe,
      switchOrganization,
      authFetch,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
