const API_URL = 'http://127.0.0.1:8000';

// Helper: fetch with a timeout so requests don't hang forever
// when the backend is unreachable or restarting
async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 10000): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    return res;
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw new Error('Request timed out — is the backend server running?');
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export const getAuthHeaders = () => {
  const token = localStorage.getItem("accessToken");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export const api = {
  // Auth endpoints
  async register(data: any) {
    const res = await fetchWithTimeout(`${API_URL}/auth/register`, {
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
    const res = await fetchWithTimeout(`${API_URL}/auth/login`, {
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
    const res = await fetchWithTimeout(`${API_URL}/auth/me`, {
      headers: getAuthHeaders(),
    }, 5000); // shorter timeout for session check
    if (!res.ok) throw new Error("Not authenticated");
    return res.json();
  },

  // Document endpoints
  async saveDocument(data: any) {
    const res = await fetchWithTimeout(`${API_URL}/documents/save`, {
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
    projectId?: string,
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
    if (projectId) params.append("project_id", projectId);
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);

    const res = await fetchWithTimeout(`${API_URL}/documents/?${params.toString()}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch documents");
    return res.json();
  },

  async getDocument(id: string) {
    const res = await fetchWithTimeout(`${API_URL}/documents/${id}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch document");
    return res.json();
  },

  async deleteDocument(id: string) {
    const res = await fetchWithTimeout(`${API_URL}/documents/${id}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to delete document");
    return res.json();
  },

  async bulkDeleteDocuments(documentIds: string[]) {
    const res = await fetchWithTimeout(`${API_URL}/documents/bulk-delete`, {
      method: "POST",
      headers: {
        ...getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ document_ids: documentIds }),
    });
    if (!res.ok) throw new Error("Failed to delete selected documents");
    return res.json();
  },

  async getProfile() {
    const res = await fetchWithTimeout(`${API_URL}/auth/profile`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch profile");
    return res.json();
  },

  async updateUsername(username: string) {
    const res = await fetchWithTimeout(`${API_URL}/auth/username`, {
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
    const res = await fetchWithTimeout(`${API_URL}/auth/password`, {
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
    const res = await fetchWithTimeout(`${API_URL}/auth/me`, {
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
    const res = await fetchWithTimeout(`${API_URL}/documents/${id}/export?format=${format}`, {
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
  },

  async retryDocument(id: string) {
    const res = await fetchWithTimeout(`${API_URL}/documents/${id}/retry`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to retry document processing");
    return res.json();
  },

  async getDocumentEvents(id: string) {
    const res = await fetchWithTimeout(`${API_URL}/documents/${id}/events`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch document events");
    return res.json();
  },

  async getDocumentExtractionMonitor(id: string) {
    const res = await fetchWithTimeout(`${API_URL}/documents/${id}/extraction-monitor`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch extraction monitor data");
    return res.json();
  },

  async getDocumentStatus(id: string) {
    const res = await fetchWithTimeout(`${API_URL}/documents/${id}/status`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch document status metadata");
    return res.json();
  },

  // Facts / Knowledge base endpoints
  async getProjectFacts(projectId: string) {
    const res = await fetchWithTimeout(`${API_URL}/projects/${projectId}/facts/review`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch project facts");
    return res.json();
  },

  async approveFact(factId: string) {
    const res = await fetchWithTimeout(`${API_URL}/facts/${factId}/approve`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to approve fact");
    return res.json();
  },

  async rejectFact(factId: string) {
    const res = await fetchWithTimeout(`${API_URL}/facts/${factId}/reject`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to reject fact");
    return res.json();
  },

  async modifyFact(factId: string, predicate: string, objectText: string) {
    const res = await fetchWithTimeout(`${API_URL}/facts/${factId}/modify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ predicate, object_text: objectText }),
    });
    if (!res.ok) throw new Error("Failed to modify fact");
    return res.json();
  },

  async undoFactAction(factId: string) {
    const res = await fetchWithTimeout(`${API_URL}/facts/${factId}/undo`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to undo last fact action");
    return res.json();
  },

  async importGoogleSheet(sheetUrl: string, projectId?: string) {
    const res = await fetchWithTimeout(`${API_URL}/import/google-sheet`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ sheet_url: sheetUrl, project_id: projectId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to import Google Sheet" }));
      throw new Error(err.detail || "Failed to import Google Sheet");
    }
    return res.json();
  }
};

