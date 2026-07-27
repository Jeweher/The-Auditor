import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { AuthTokens } from "../types";
import * as authApi from "../api/auth";

interface AuthState {
  isAuthenticated: boolean;
  email: string | null;
  profilePhoto: string | null;
  setProfilePhoto: (url: string | null) => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [email, setEmail] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [profilePhoto, setProfilePhotoState] = useState<string | null>(null);

  // On mount, restore session from localStorage if a token exists.
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const storedEmail = localStorage.getItem("user_email");
    const storedPhoto = localStorage.getItem("user_profile_photo");
    if (token) {
      setIsAuthenticated(true);
      setEmail(storedEmail);
      setProfilePhoto(storedPhoto);
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

  async function login(emailArg: string, password: string) {
    const tokens: AuthTokens = await authApi.login(emailArg, password);
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
    localStorage.setItem("user_email", emailArg);
    setEmail(emailArg);
    setIsAuthenticated(true);
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
    localStorage.removeItem("user_profile_photo");
    setEmail(null);
    setIsAuthenticated(false);
    setProfilePhotoState(null);
  }

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, email, profilePhoto, setProfilePhoto, login, logout }}
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