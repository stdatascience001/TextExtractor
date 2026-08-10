const API_URL = "http://127.0.0.1:8000";

// Timeout wrapper so requests fail fast instead of hanging forever
async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 10000): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (err: any) {
    if (err.name === 'AbortError') throw new Error('Request timed out — backend may be down');
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

const getAuthHeaders = () => {
  const token = localStorage.getItem("accessToken");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export const axiosInstance = {
  async get(url: string, config?: any) {
    const fullUrl = url.startsWith("http") ? url : `${API_URL}${url}`;
    const res = await fetchWithTimeout(fullUrl, {
      method: "GET",
      headers: {
        ...getAuthHeaders(),
        ...config?.headers,
      },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail || "Request failed");
    }
    return { data: await res.json() };
  },

  async post(url: string, data: any, config?: any) {
    const fullUrl = url.startsWith("http") ? url : `${API_URL}${url}`;
    const res = await fetchWithTimeout(fullUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
        ...config?.headers,
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail || "Request failed");
    }
    return { data: await res.json() };
  },

  async put(url: string, data: any, config?: any) {
    const fullUrl = url.startsWith("http") ? url : `${API_URL}${url}`;
    const res = await fetchWithTimeout(fullUrl, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
        ...config?.headers,
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail || "Request failed");
    }
    return { data: await res.json() };
  },

  async patch(url: string, data: any, config?: any) {
    const fullUrl = url.startsWith("http") ? url : `${API_URL}${url}`;
    const res = await fetchWithTimeout(fullUrl, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
        ...config?.headers,
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail || "Request failed");
    }
    return { data: await res.json() };
  },

  async delete(url: string, config?: any) {
    const fullUrl = url.startsWith("http") ? url : `${API_URL}${url}`;
    const res = await fetchWithTimeout(fullUrl, {
      method: "DELETE",
      headers: {
        ...getAuthHeaders(),
        ...config?.headers,
      },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail || "Request failed");
    }
    return { data: await res.json() };
  },
};
export default axiosInstance;
