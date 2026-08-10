import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import { ExtractedDocument } from "../lib/mockApi";

interface User {
  id: string;
  username: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  pendingDocument: ExtractedDocument | null;
  setPendingDocument: (doc: ExtractedDocument | null) => void;
  login: (tokens: { access_token: string; refresh_token: string }) => Promise<void>;
  logout: () => void;
}

const parseJwt = (token: string) => {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      window.atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    return null;
  }
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [pendingDocument, setPendingDocument] = useState<ExtractedDocument | null>(null);

  const logout = useCallback(() => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    localStorage.removeItem("pendingDocument");
    setUser(null);
    setPendingDocument(null);
  }, []);

  const fetchUser = useCallback(async () => {
    try {
      if (localStorage.getItem("accessToken")) {
        const userData = await api.getMe();
        setUser(userData);
      }
    } catch (error) {
      console.error("Failed to fetch user", error);
      logout();
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  const checkTokenExpiry = useCallback(() => {
    const token = localStorage.getItem("accessToken");
    if (token) {
      const payload = parseJwt(token);
      if (payload && payload.exp) {
        const currentTime = Math.floor(Date.now() / 1000);
        if (payload.exp < currentTime) {
          console.warn("Session token expired, logging out...");
          logout();
          return true;
        }
      } else {
        console.warn("Invalid session token structure, logging out...");
        logout();
        return true;
      }
    }
    return false;
  }, [logout]);

  useEffect(() => {
    const expired = checkTokenExpiry();
    if (!expired) {
      fetchUser();
    }
    
    // Check if there's a pending document saved in localStorage across hard reloads
    const savedDoc = localStorage.getItem("pendingDocument");
    if (savedDoc) {
      try {
        setPendingDocument(JSON.parse(savedDoc));
      } catch (e) {
        console.error("Failed to parse pending doc");
      }
    }

    const interval = setInterval(() => {
      checkTokenExpiry();
    }, 5000); // Check expiry status every 5 seconds

    return () => clearInterval(interval);
  }, [fetchUser, checkTokenExpiry]);

  // Global fetch interceptor to catch any 401 Unauthorized API responses
  useEffect(() => {
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      try {
        const response = await originalFetch(...args);
        if (response.status === 401) {
          const url = typeof args[0] === "string" ? args[0] : (args[0] as Request).url;
          // Exclude login and registration requests to prevent interference with credentials validation
          if (!url.includes("/auth/login") && !url.includes("/auth/register")) {
            console.warn("Unauthorized API access (401), logging out...");
            logout();
          }
        }
        return response;
      } catch (err) {
        throw err;
      }
    };

    return () => {
      window.fetch = originalFetch;
    };
  }, [logout]);

  const handleSetPendingDocument = (doc: ExtractedDocument | null) => {
    setPendingDocument(doc);
    if (doc) {
      localStorage.setItem("pendingDocument", JSON.stringify(doc));
    } else {
      localStorage.removeItem("pendingDocument");
    }
  };

  const login = async (tokens: { access_token: string; refresh_token: string }) => {
    localStorage.setItem("accessToken", tokens.access_token);
    localStorage.setItem("refreshToken", tokens.refresh_token);
    await fetchUser();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        pendingDocument,
        setPendingDocument: handleSetPendingDocument,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
