import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { AuthTokens } from "../types";
import * as authApi from "../api/auth";

interface AuthState {
  isAuthenticated: boolean;
  authReady: boolean;
  email: string | null;
  fullName: string | null;
  companyName: string | null;
  role: string | null;
  profilePhoto: string | null;
  setProfilePhoto: (url: string | null) => void;
  login: (email: string, password: string) => Promise<string | null>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [email, setEmail] = useState<string | null>(null);
  const [fullName, setFullName] = useState<string | null>(null);
  const [companyName, setCompanyName] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [profilePhoto, setProfilePhotoState] = useState<string | null>(null);
  const [authReady, setAuthReady] = useState(false);

  // Pull the authoritative profile from the backend and sync it everywhere
  // (state + localStorage) — this is the single source of truth, never a
  // value cached from whichever account last registered on this browser.
  async function syncProfile(): Promise<string | null> {
    try {
      const me = await authApi.getMe();
      setEmail(me.email);
      setFullName(me.full_name);
      setCompanyName(me.company_name || null);
      setRole(me.role);
      setProfilePhotoState(me.profile_photo || null);
      localStorage.setItem("user_email", me.email);
      localStorage.setItem("user_full_name", me.full_name);
      if (me.company_name) localStorage.setItem("user_company_name", me.company_name);
      else localStorage.removeItem("user_company_name");
      localStorage.setItem("user_role", me.role);
      if (me.profile_photo) localStorage.setItem("user_profile_photo", me.profile_photo);
      else localStorage.removeItem("user_profile_photo");
      return me.role;
    } catch {
      // If /me fails (expired token, etc.), fall back to whatever is cached
      // rather than blanking the UI — the axios 401 interceptor already
      // handles forcing a re-login when the token is truly invalid.
      return null;
    }
  }

  // On mount, restore session from localStorage if a token exists, then
  // refresh from the server to correct any stale cached values. authReady
  // only flips to true once this initial check is fully resolved — guards
  // like AdminRoute wait on it, so a hard page reload (typing a URL, F5)
  // never makes a redirect decision based on the still-empty initial state.
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      setIsAuthenticated(true);
      setEmail(localStorage.getItem("user_email"));
      setFullName(localStorage.getItem("user_full_name"));
      setCompanyName(localStorage.getItem("user_company_name"));
      setRole(localStorage.getItem("user_role"));
      setProfilePhotoState(localStorage.getItem("user_profile_photo"));
      syncProfile().finally(() => setAuthReady(true));
    } else {
      setAuthReady(true);
    }
  }, []);

  function setProfilePhoto(url: string | null) {
    setProfilePhotoState(url);
    if (url) {
      localStorage.setItem("user_profile_photo", url);
    } else {
      localStorage.removeItem("user_profile_photo");
    }
  }

  async function login(emailArg: string, password: string): Promise<string | null> {
    const tokens: AuthTokens = await authApi.login(emailArg, password);
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
    setIsAuthenticated(true);
    // Always fetch the real profile right after login — this is what
    // guarantees the greeting/avatar reflect the account that just signed
    // in, not a name left over from a previous account on this browser.
    // Returning the role directly (rather than relying on context state)
    // avoids a race: state updates aren't guaranteed to be visible on the
    // very next line, but this return value is.
    return await syncProfile();
  }

  async function logout() {
    const refresh = localStorage.getItem("refresh_token");
    try {
      if (refresh) await authApi.logout(refresh);
    } catch {
      // Even if the server call fails, clear the local session.
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_email");
    localStorage.removeItem("user_full_name");
    localStorage.removeItem("user_company_name");
    localStorage.removeItem("user_role");
    localStorage.removeItem("user_profile_photo");
    setEmail(null);
    setFullName(null);
    setCompanyName(null);
    setRole(null);
    setIsAuthenticated(false);
    setProfilePhotoState(null);
  }

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        authReady,
        email,
        fullName,
        companyName,
        role,
        profilePhoto,
        setProfilePhoto,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}