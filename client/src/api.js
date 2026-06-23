// Wrapper de fetch con credenciales de sesión. Ante 401 dispara el handler global.

let onUnauthorized = () => {};
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Error ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

async function request(method, path, body) {
  let res;
  try {
    res = await fetch(path, {
      method,
      credentials: "include",
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    throw new ApiError(0, "No se pudo conectar. Reintenta.");
  }

  if (res.status === 401) {
    onUnauthorized();
    throw new ApiError(401, "No autenticado");
  }

  const isJson = (res.headers.get("content-type") || "").includes("application/json");
  const payload = isJson ? await res.json() : await res.text();

  if (!res.ok) {
    const detail = isJson && payload && payload.detail ? payload.detail : `Error ${res.status}`;
    throw new ApiError(res.status, detail);
  }
  return payload;
}

export const api = {
  get: (p) => request("GET", p),
  post: (p, b) => request("POST", p, b ?? {}),
  patch: (p, b) => request("PATCH", p, b ?? {}),
  put: (p, b) => request("PUT", p, b ?? {}),
  del: (p) => request("DELETE", p),
  getText: async (p) => {
    const res = await fetch(p, { credentials: "include" });
    if (res.status === 401) {
      onUnauthorized();
      throw new ApiError(401, "No autenticado");
    }
    if (!res.ok) throw new ApiError(res.status, "Error");
    return res.text();
  },
  // Envío multipart (subida de archivos, import CSV). No fija Content-Type (lo pone el navegador).
  postForm: async (p, formData) => {
    let res;
    try {
      res = await fetch(p, { method: "POST", credentials: "include", body: formData });
    } catch (e) {
      throw new ApiError(0, "No se pudo conectar. Reintenta.");
    }
    if (res.status === 401) {
      onUnauthorized();
      throw new ApiError(401, "No autenticado");
    }
    const isJson = (res.headers.get("content-type") || "").includes("application/json");
    const payload = isJson ? await res.json() : await res.text();
    if (!res.ok) {
      const detail = isJson && payload && payload.detail ? payload.detail : `Error ${res.status}`;
      throw new ApiError(res.status, detail);
    }
    return payload;
  },
};
