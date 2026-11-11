import { Fragment, useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { api, apiStream, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Icon, type IconName } from "./Icon";

interface Topic { id: string; icon: string; title: string; subtitle: string; body: string; page: string | null; link: string | null }
interface Message { role: "user" | "assistant"; text: string; topic?: Topic; error?: boolean; pending?: boolean }

/** "**qalin**" ni ajratadi, qatorlarni saqlaydi. AI javobi va tayyor mavzular uchun. */
function Rich({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, i) => (
        <Fragment key={i}>
          {i > 0 && <br />}
          {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
            part.startsWith("**") && part.endsWith("**") && part.length > 4
              ? <b key={j}>{part.slice(2, -2)}</b>
              : <Fragment key={j}>{part}</Fragment>)}
        </Fragment>
      ))}
    </>
  );
}

/** Backend mavzu belgisini (emoji) ilova ikonkasiga moslaydi. */
const TOPIC_ICONS: Record<string, IconName> = {
  "🧾": "cart", "🏷": "tag", "👤": "user", "🎁": "gift", "↩": "undo", "📦": "box", "📈": "receipt", "🏬": "store",
  "✅": "check-circle", "👕": "shirt", "✎": "pencil", "📥": "inbox", "🔁": "transfer", "💡": "bulb", "📊": "chart",
  "⚙": "sliders", "★": "star", "👥": "users",
};

function Bubble({ m, onLink }: { m: Message; onLink: (page: string) => void }) {
  if (m.role === "user") return <div className="assistant-msg user">{m.text}</div>;
  return (
    <div className={`assistant-msg bot ${m.error ? "error" : ""}`}>
      {m.pending && !m.text ? <span className="assistant-typing" aria-label="Yozilmoqda"><i /><i /><i /></span> : <Rich text={m.text} />}
      {m.topic?.page && m.topic.link && (
        <div style={{ marginTop: 10 }}>
          <button className="btn btn-secondary btn-sm" onClick={() => onLink(m.topic!.page!)}>{m.topic.link} <Icon name="arrow-right" size={15} /></button>
        </div>
      )}
    </div>
  );
}

/** HEMIS'dagi kabi yon panel: dasturdan foydalanishni o'rgatadi. Xodimning o'rniga ish qilmaydi. */
export function Assistant({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { me } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [topics, setTopics] = useState<Topic[] | null>(null);
  const [aiReady, setAiReady] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Mavzular panel birinchi ochilganda yuklanadi (rol o'zgarsa qayta).
  useEffect(() => {
    if (!open || topics) return;
    api<{ topics: Topic[]; ai_configured: boolean }>("/assistant/topics/")
      .then((d) => { setTopics(d.topics); setAiReady(d.ai_configured); setLoadError(null); })
      .catch((e: Error) => setLoadError(e.message));
  }, [open, topics]);
  useEffect(() => { setTopics(null); setMessages([]); }, [me?.id, me?.role]);

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    const onKey = (e: globalThis.KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages]);

  useEffect(() => () => abort.current?.abort(), []);

  function showTopic(t: Topic) {
    setMessages((m) => [...m, { role: "user", text: t.title }, { role: "assistant", text: t.body, topic: t }]);
  }

  function goTo(page: string) {
    navigate(page);
    if (window.matchMedia("(max-width: 760px)").matches) onClose();
  }

  async function ask(e?: FormEvent) {
    e?.preventDefault();
    const question = input.trim();
    if (!question || busy) return;
    const history = messages.filter((m) => !m.error && !m.pending).slice(-6).map((m) => ({ role: m.role, text: m.text }));
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", text: question }, { role: "assistant", text: "", pending: true }]);
    const update = (fn: (last: Message) => Message) =>
      setMessages((m) => [...m.slice(0, -1), fn(m[m.length - 1])]);
    abort.current = new AbortController();
    try {
      await apiStream("/assistant/ask/", { question, page: location.pathname, history },
                      (chunk) => update((last) => ({ ...last, text: last.text + chunk })), abort.current.signal);
      update((last) => ({ ...last, pending: false }));
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      const msg = err instanceof ApiError ? err.message : "Javob olinmadi. Qayta urinib ko'ring.";
      update(() => ({ role: "assistant", text: `${msg}\n\nPastdagi mavzular tugmasi orqali tayyor mavzulardan foydalanishingiz mumkin.`, error: true }));
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  function onInputKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void ask();
    }
  }

  function home() {
    abort.current?.abort();
    setBusy(false);
    setMessages([]);
  }

  if (!open) return null;

  let body: ReactNode;
  if (messages.length === 0) {
    body = (
      <div className="assistant-home">
        <div className="assistant-logo" aria-hidden="true"><Icon name="sparkles" size={26} /></div>
        <h2 style={{ margin: "8px 0 4px" }}>Xush kelibsiz!</h2>
        <p className="muted" style={{ margin: "0 0 16px", textAlign: "center" }}>
          Dasturdan qanday foydalanishni o'rgataman. Mavzuni tanlang yoki savolingizni yozing.
        </p>
        {loadError ? <div className="alert alert-error">{loadError}</div> : !topics ? <div className="spinner" /> : (
          <div className="assistant-topics">
            {topics.map((t) => (
              <button key={t.id} className="assistant-topic" onClick={() => showTopic(t)}>
                <span className="assistant-topic-icon" aria-hidden="true">{TOPIC_ICONS[t.icon] ? <Icon name={TOPIC_ICONS[t.icon]} /> : t.icon}</span>
                <span>
                  <span className="assistant-topic-title">{t.title}</span>
                  <span className="muted">{t.subtitle}</span>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  } else {
    body = messages.map((m, i) => <Bubble key={i} m={m} onLink={goTo} />);
  }

  return (
    <>
      <div className="assistant-backdrop" onClick={onClose} aria-hidden="true" />
      <aside className="assistant-panel" role="dialog" aria-label="Yordamchi">
        <header className="assistant-head">
          <b className="row" style={{ gap: 8 }}><Icon name="sparkles" /> Yordamchi</b>
          <button className="btn btn-secondary btn-sm" onClick={onClose} aria-label="Yopish"><Icon name="x" size={16} /></button>
        </header>
        <div className="assistant-body" ref={listRef}>{body}</div>
        <form className="assistant-input" onSubmit={ask}>
          <textarea
            ref={inputRef} className="input" rows={2} maxLength={500} value={input}
            placeholder={aiReady ? "Nima haqida bilmoqchisiz?" : "AI sozlanmagan — tayyor mavzulardan foydalaning"}
            disabled={!aiReady} onChange={(e) => setInput(e.target.value)} onKeyDown={onInputKey}
            aria-label="Savol"
          />
          <div className="spread">
            <div className="row" style={{ gap: 6 }}>
              <button type="button" className="btn btn-secondary btn-sm" onClick={home} title="Tayyor mavzular"
                      aria-label="Tayyor mavzular"><Icon name="grid" size={16} /></button>
              <span className="badge badge-neutral">{aiReady ? "Gemini" : "Faqat tayyor mavzular"}</span>
            </div>
            <button className="btn btn-primary btn-sm" disabled={!aiReady || busy || !input.trim()} aria-label="Yuborish">
              {busy ? "…" : <>Yuborish <Icon name="send" size={15} /></>}
            </button>
          </div>
          <span className="muted" style={{ fontSize: 11 }}>
            Yordamchi faqat dasturdan foydalanishni o'rgatadi, sizning o'rningizga ish qilmaydi va xato qilishi mumkin.
          </span>
        </form>
      </aside>
    </>
  );
}
