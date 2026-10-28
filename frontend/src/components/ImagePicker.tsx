import { useEffect, useRef, useState } from "react";

import { ProductThumb } from "./ui";

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPT = "image/jpeg,image/png,image/webp";

/** Rasm tanlash: oldindan ko'rish va hajmni tekshirish. Serverga yuklashni chaqiruvchi o'zi qiladi. */
export function ImagePicker({ current, onPick, onRemove, busy }: {
  current: string | null;
  onPick: (file: File) => void;
  onRemove?: () => void;
  busy?: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  function pick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!ACCEPT.split(",").includes(file.type)) return setError("Faqat JPG, PNG yoki WebP rasm yuklang.");
    if (file.size > MAX_BYTES) return setError("Rasm hajmi 10 MB dan oshmasligi kerak.");
    setError(null);
    setPreview(URL.createObjectURL(file));
    onPick(file);
  }

  const shown = preview ?? current;
  return (
    <div className="stack" style={{ gap: 4 }}>
      <div className="image-picker">
        <ProductThumb src={shown} size={96} alt="Tovar rasmi" />
        <input ref={input} type="file" accept={ACCEPT} hidden onChange={pick} />
        <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => input.current?.click()}>
          {shown ? "Rasmni almashtirish" : "Rasm tanlash"}
        </button>
        {shown && onRemove && (
          <button type="button" className="btn btn-secondary btn-sm" disabled={busy}
                  onClick={() => { setPreview(null); onRemove(); }}>
            Olib tashlash
          </button>
        )}
      </div>
      {error && <span className="field-error">{error}</span>}
    </div>
  );
}
