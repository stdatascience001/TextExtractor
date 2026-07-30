const API_URL = 'http://localhost:8000';

export const getAuthHeaders = () => {
  const token = localStorage.getItem("accessToken");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export const api = {
  // Auth endpoints
  async register(data: any) {
    const res = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Registration failed" }));
      throw new Error(err.detail || "Registration failed");
    }
    return res.json();
  },

  async login(data: any) {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || "Login failed");
    }
    return res.json();
  },

  async getMe() {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Not authenticated");
    return res.json();
  },

  // Document endpoints
  async saveDocument(data: any) {
    const res = await fetch(`${API_URL}/documents/save`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to save document" }));
      throw new Error(err.detail || "Failed to save document");
    }
    return res.json();
  },

  async getDocuments(
    skip: number = 0, 
    limit: number = 20,
    query?: string,
    startDate?: string,
    endDate?: string,
    sortBy: string = "created_at",
    sortOrder: string = "desc"
  ) {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
      sort_by: sortBy,
      sort_order: sortOrder
    });

    if (query) params.append("query", query);
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);

    const res = await fetch(`${API_URL}/documents/?${params.toString()}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch documents");
    return res.json();
  },

  async getDocument(id: string) {
    const res = await fetch(`${API_URL}/documents/${id}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch document");
    return res.json();
  },

  async deleteDocument(id: string) {
    const res = await fetch(`${API_URL}/documents/${id}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to delete document");
    return res.json();
  },

  async getProfile() {
    const res = await fetch(`${API_URL}/auth/profile`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch profile");
    return res.json();
  },

  async updateUsername(username: string) {
    const res = await fetch(`${API_URL}/auth/username`, {
      method: "PUT",
      headers: {
        ...getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update username");
    }
    return res.json();
  },

  async changePassword(current_password: string, new_password: string) {
    const res = await fetch(`${API_URL}/auth/password`, {
      method: "PUT",
      headers: {
        ...getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ current_password, new_password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to change password");
    }
    return res.json();
  },

  async deleteAccount() {
    const res = await fetch(`${API_URL}/auth/me`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to delete account");
    }
    return res.json();
  },

  async exportDocument(id: string, format: "text" | "json" | "csv") {
    const res = await fetch(`${API_URL}/documents/${id}/export?format=${format}`, {
      headers: getAuthHeaders(),
    });
    
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to export document");
    }
    
    // Handle the binary/text blob response
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition");
    let filename = `export-${id}.${format === "text" ? "txt" : format}`;
    
    if (disposition && disposition.indexOf("filename=") !== -1) {
      const matches = /filename="([^"]*)"/.exec(disposition);
      if (matches != null && matches[1]) filename = matches[1];
    }
    
    // Trigger download via DOM
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    // Cleanup
    window.URL.revokeObjectURL(url);
    a.remove();
  }
};
