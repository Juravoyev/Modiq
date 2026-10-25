/** Backend bilan aloqa: JWT tokenlar, avtomatik yangilash va DRF xatolarini tushunarli ko'rinishga keltirish. */

const ACCESS = "modiq.access";
const REFRESH = "modiq.refresh";

export class ApiError extends Error {
  status: number;
  code?: string;
  fields: Record<string, string>;

  constructor(status: number, message: string, fields: Record<string, string> = {}, code?: string) {
    super(message);
    this.status = status;
    this.fields = fields;
    this.code = code;
  }
}

export const tokens = {
  get access() { return localStorage.getItem(ACCESS); },
  get refresh() { return localStorage.getItem(REFRESH); },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS, access);
    if (refresh) localStorage.setItem(REFRESH, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
  },
};

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(fn: () => void) { onUnauthorized = fn; }

function flatten(value: unknown): string {
  if (Array.isArray(value)) return value.map(flatten).join(" ");
  if (value && typeof value === "object") return Object.values(value).map(flatten).join(" ");
  return String(value ?? "");
}

function toError(status: number, body: unknown): ApiError {
  if (status === 0) return new ApiError(0, "Server bilan aloqa yo'q. Internetni tekshiring.");
  if (status >= 500) return new ApiError(status, "Serverda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.");
  if (body && typeof body === "object" && !Array.isArray(body)) {
    const obj = body as Record<string, unknown>;
    const fields: Record<string, string> = {};
    for (const [k, v] of Object.entries(obj)) {
      if (!["detail", "code", "non_field_errors"].includes(k)) fields[k] = flatten(v);
    }
    const message = flatten(obj.detail ?? obj.non_field_errors ?? "") ||
      (Object.keys(fields).length ? "Ma'lumotlarni tekshiring." : "So'rov bajarilmadi.");
    return new ApiError(status, message, fields, typeof obj.code === "string" ? obj.code : flatten(obj.code) || undefined);
  }
  if (status === 403) return new ApiError(status, "Bu amal uchun ruxsatingiz yo'q.");
  if (status === 404) return new ApiError(status, "Ma'lumot topilmadi.");
  return new ApiError(status, "So'rov bajarilmadi.");
}

async function refreshAccess(): Promise<boolean> {
  const refresh = tokens.refresh;
  if (!refresh) return false;
  const res = await fetch("/api/auth/refresh/", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh }),
  });
  if (!res.ok) return false;
  const data = await res.json();
  tokens.set(data.access, data.refresh);
  return true;
}

export async function api<T>(path: string, options: { method?: string; body?: unknown; auth?: boolean } = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;
  const send = () => {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth && tokens.access) headers.Authorization = `Bearer ${tokens.access}`;
    return fetch(`/api${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  };

  let res: Response;
  try {
    res = await send();
    if (res.status === 401 && auth && (await refreshAccess())) res = await send();
  } catch {
    throw toError(0, null);
  }
  if (res.status === 401 && auth) {
    tokens.clear();
    onUnauthorized();
  }
  const text = await res.text();
  let data: unknown = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }
  if (!res.ok) throw toError(res.status, data);
  return data as T;
}

export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}
