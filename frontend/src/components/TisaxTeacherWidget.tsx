import { useEffect, useRef, useState } from "react";
import * as publicApi from "../api/publicAssistant";
import type { ChatTurn } from "../api/publicAssistant";

interface Entry {
  id: string;
  role: "bot" | "user";
  text: string;
}

function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}
function sleep(ms: number) {
  return new Promise((res) => setTimeout(res, ms));
}

const CHAR_DELAY_MS = 12;
const SUGGESTIONS = ["What is TISAX?", "What does ML3 mean?", "What is the VDA ISA?"];

export default function TisaxTeacherWidget() {
  const [open, setOpen] = useState(false);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [streaming, setStreaming] = useState<{ id: string; shown: string } | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const greetedRef = useRef(false);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [entries, streaming]);

  async function say(text: string) {
    const id = uid();
    setStreaming({ id, shown: "" });
    for (let i = 1; i <= text.length; i++) {
      await sleep(CHAR_DELAY_MS);
      setStreaming((s) => (s && s.id === id ? { id, shown: text.slice(0, i) } : s));
    }
    await sleep(100);
    setEntries((prev) => [...prev, { id, role: "bot", text }]);
    setStreaming(null);
  }

  function handleOpen() {
    setOpen(true);
    if (!greetedRef.current) {
      greetedRef.current = true;
      say(
        "Hi! 👋 I'm your TISAX teacher. Ask me anything about the standard — what it is, how maturity levels work, what an assessment involves..."
      );
    }
  }

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    setErrorMsg(null);
    setBusy(true);
    setEntries((prev) => [...prev, { id: uid(), role: "user", text: message }]);
    setDraft("");
    try {
      const history: ChatTurn[] = entries.map((e) => ({
        role: e.role === "bot" ? "assistant" : "user",
        content: e.text,
      }));
      const reply = await publicApi.askTisaxAssistant(message, history);
      await say(reply);
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      setErrorMsg(
        status === 429
          ? "You've reached the question limit for now — please try again a bit later."
          : "Something went wrong. Please try again."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative flex justify-center lg:justify-end">
      {/* Robot illustration + speech bubble (closed state) */}
      <button
        onClick={handleOpen}
        className={`relative flex flex-col items-center focus:outline-none ${open ? "invisible" : ""}`}
        aria-label="Ask the TISAX assistant"
      >
        <div style={{ perspective: "700px" }} className="relative">
          <div className="absolute inset-0 -z-10 animate-orb-pulse rounded-full bg-brand-400 blur-2xl" />
          <RobotMascot className="animate-robot-idle" style={{ transformStyle: "preserve-3d" }} />
        </div>
        <div className="animate-bubble-in relative -mt-1 max-w-[230px] rounded-2xl rounded-bl-sm bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-lg ring-1 ring-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-700">
          <span className="absolute -top-1.5 left-7 h-3 w-3 rotate-45 bg-white ring-1 ring-slate-200 dark:bg-slate-800 dark:ring-slate-700" />
          Click here to chat — any question?
        </div>
      </button>

      {/* Chat panel (open state) */}
      {open && (
        <div className="absolute right-0 top-0 z-20 w-[22rem] max-w-[90vw] origin-top animate-widget-in overflow-hidden rounded-2xl border border-brand-200 bg-white shadow-xl dark:border-brand-500/20 dark:bg-slate-800">
          <div className="flex items-center justify-between border-b border-slate-100 bg-brand-50 px-4 py-3 dark:border-slate-700 dark:bg-brand-500/10">
            <div className="flex items-center gap-2">
              <RobotMascot small />
              <div>
                <p className="text-sm font-semibold text-slate-800 dark:text-white">Ask about TISAX</p>
                <p className="text-xs text-slate-400">No account needed</p>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="rounded-full p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-700"
              aria-label="Close"
            >
              ✕
            </button>
          </div>

          <div ref={scrollContainerRef} className="h-72 space-y-3 overflow-y-auto px-4 py-4">
            {entries.map((e) => (
              <Bubble key={e.id} role={e.role} text={e.text} />
            ))}
            {streaming && <Bubble role="bot" text={streaming.shown + "▍"} />}
            {errorMsg && <p className="text-xs text-rose-500">{errorMsg}</p>}
          </div>

          {entries.length === 0 && !streaming && (
            <div className="flex flex-wrap gap-2 px-4 pb-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-500 hover:border-brand-300 hover:text-brand-600 dark:border-slate-700 dark:text-slate-400"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          <div className="flex gap-2 border-t border-slate-100 p-3 dark:border-slate-700">
            <input
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send(draft)}
              disabled={busy || streaming !== null}
              placeholder="Ask a question..."
              autoFocus
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 disabled:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            />
            <button
              onClick={() => send(draft)}
              disabled={busy || streaming !== null || !draft.trim()}
              className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            >
              Ask
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function RobotMascot({
  small = false,
  className = "",
  style,
}: {
  small?: boolean;
  className?: string;
  style?: React.CSSProperties;
}) {
  const size = small ? 28 : 210;
  return (
    <svg width={size} height={size} viewBox="0 0 140 160" className={className} style={style}>
      <defs>
        <linearGradient id="botBody" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#bff0ee" />
          <stop offset="45%" stopColor="#1fa3a6" />
          <stop offset="100%" stopColor="#0f4d52" />
        </linearGradient>
        <radialGradient id="botVisor" cx="35%" cy="30%" r="75%">
          <stop offset="0%" stopColor="#e9fffe" />
          <stop offset="60%" stopColor="#7adbd9" />
          <stop offset="100%" stopColor="#166970" />
        </radialGradient>
      </defs>

      {/* antenna */}
      <line x1="70" y1="14" x2="70" y2="2" stroke="#1fa3a6" strokeWidth="3" strokeLinecap="round" />
      <circle cx="70" cy="2" r="4" fill="#7adbd9" />

      {/* head */}
      <rect x="30" y="16" width="80" height="62" rx="26" fill="url(#botBody)" />
      {/* visor */}
      <rect x="42" y="34" width="56" height="30" rx="14" fill="url(#botVisor)" opacity="0.9" />
      <circle cx="58" cy="49" r="5" fill="#083c40" />
      <circle cx="82" cy="49" r="5" fill="#083c40" />

      {/* body */}
      <path
        d="M 40 82 Q 70 74 100 82 L 108 132 Q 70 148 32 132 Z"
        fill="url(#botBody)"
        opacity="0.95"
      />
      {/* circuit lines */}
      <path
        d="M 45 96 Q 70 104 95 96"
        stroke="#e9fffe"
        strokeWidth="1.5"
        fill="none"
        opacity="0.6"
      />
      <path
        d="M 42 112 Q 70 122 98 112"
        stroke="#e9fffe"
        strokeWidth="1.5"
        fill="none"
        opacity="0.4"
      />

      {/* arms */}
      <ellipse cx="26" cy="100" rx="8" ry="16" fill="#1fa3a6" opacity="0.85" />
      <ellipse cx="114" cy="100" rx="8" ry="16" fill="#1fa3a6" opacity="0.85" />
    </svg>
  );
}

function Bubble({ role, text }: { role: "bot" | "user"; text: string }) {
  const isBot = role === "bot";
  return (
    <div className={`flex ${isBot ? "" : "justify-end"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm ${
          isBot
            ? "rounded-bl-sm bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100"
            : "rounded-br-sm bg-brand-500 text-white"
        }`}
      >
        {text}
      </div>
    </div>
  );
}