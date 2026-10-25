/** "120000.00" -> "120 000 so'm" */
export function money(value: string | number | null | undefined): string {
  const n = typeof value === "string" ? Number(value) : (value ?? 0);
  const rounded = Math.round(n * 100) / 100;
  const [int, frac] = Math.abs(rounded).toFixed(2).split(".");
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${rounded < 0 ? "-" : ""}${grouped}${frac !== "00" ? "," + frac : ""} so'm`;
}

/** ISO sana -> "25.10.2026 14:05" (Toshkent vaqti) */
export function dateTime(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    timeZone: "Asia/Tashkent", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

/** Har bir savdo uchun yangi UUID. HTTP (masalan, telefon lokal tarmoqda) da ham ishlaydi. */
export function newIdempotencyKey(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}
