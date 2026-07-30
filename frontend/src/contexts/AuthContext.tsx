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

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [pendingDocument, setPendingDocument] = useState<ExtractedDocument | null>(null);

  const fetchUser = useCallback(async () => {
    try {
      if (localStorage.getItem("accessToken")) {
        const userData = await api.getMe();
        setUser(userData);
      }
    } catch (error) {
      console.error("Failed to fetch user", error);
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
    
    // Check if there's a pending document saved in localStorage across hard reloads
    const savedDoc = localStorage.getItem("pendingDocument");
    if (savedDoc) {
      try {
        setPendingDocument(JSON.parse(savedDoc));
      } catch (e) {
        console.error("Failed to parse pending doc");
      }
    }
  }, [fetchUser]);

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

  const logout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    localStorage.removeItem("pendingDocument");
    setUser(null);
    setPendingDocument(null);
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
