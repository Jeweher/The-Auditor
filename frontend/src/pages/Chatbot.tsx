import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import * as api from "../api/assessments";
import type { Assessment, ControlWithQuestions, FollowupQuestion } from "../types";
import type { AnswerResult } from "../api/assessments";
import { downloadEvidence } from "../api/assessments";

// ===== Chat transcript model =====

type Entry =
  
  | { id: string; role: "bot" | "user"; type: "text"; text: string; caption?: string; questionId?: string; answerId?: string; evidenceId?: string }
  | { id: string; role: "bot"; type: "typing" }
  | {
      id: string;
      role: "bot";
      type: "evidence-request";
      answerId: string;
      docs: string[];
      status: "idle" | "uploading" | "analyzing";
      controlId: string;
      controlNumber: string;
    }
  | {
      id: string;
      role: "bot";
      type: "finding";
      maturity: number;
      confidence: string;
      mode: string;
      finding: string;
      recommendation: string;
    };

interface AnswerOwner {
  controlId: string;
  controlNumber: string;
  evidenceExpected: boolean;
  expectedDocuments: string[];
}

function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}
function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
function sleep(ms: number) {
  return new Promise((res) => setTimeout(res, ms));
}

const CHAR_DELAY_MS = 14;

type QuickReply = { value: "yes" | "no" | "partial"; label: string; className: string };

const ALL_QUICK_REPLIES: QuickReply[] = [
  { value: "yes", label: "Yes", className: "bg-emerald-500 hover:bg-emerald-600" },
  { value: "partial", label: "Partially", className: "bg-amber-500 hover:bg-amber-600" },
  { value: "no", label: "No", className: "bg-rose-500 hover:bg-rose-600" },
];

function getQuickReplies(responseScale: string | undefined): QuickReply[] {
  if (responseScale === "yes_no") {
    return ALL_QUICK_REPLIES.filter((b) => b.value !== "partial");
  }
  return ALL_QUICK_REPLIES;
}

export default function Chatbot() {
  const { id } = useParams<{ id: string }>();
  const { email, profilePhoto, fullName, companyName } = useAuth();

  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [control, setControl] = useState<ControlWithQuestions | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [streaming, setStreaming] = useState<{ id: string; shown: string } | null>(null);
  const [activeQuestion, setActiveQuestion] = useState<FollowupQuestion | null>(null);
  const [activeEvidence, setActiveEvidence] = useState<{ answerId: string; docs: string[] } | null>(null);
  const [evidenceUi, setEvidenceUi] = useState<"idle" | "uploading" | "analyzing">("idle");
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [editingEntryId, setEditingEntryId] = useState<string | null>(null);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initializedRef = useRef(false);
  const answeredIdsRef = useRef<Set<string>>(new Set());
  const greetedControlsRef = useRef<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);
  const controlRef = useRef<ControlWithQuestions | null>(null);
  controlRef.current = control;
  const controlLockedRef = useRef(false);
  const answerControlMapRef = useRef<Record<string, AnswerOwner>>({});

  const userInitial = (email || "U").charAt(0).toUpperCase();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, streaming, activeQuestion, activeEvidence]);

  // ===== Speaking primitives =====

  async function say(text: string) {
    const id = uid();
    setStreaming({ id, shown: "" });
    for (let i = 1; i <= text.length; i++) {
      await sleep(CHAR_DELAY_MS);
      setStreaming((s) => (s && s.id === id ? { id, shown: text.slice(0, i) } : s));
    }
    await sleep(150);
    setEntries((prev) => [...prev, { id, role: "bot", type: "text", text }]);
    setStreaming(null);
  }

  function sayUser(
    text: string,
    caption?: string,
    extra?: { questionId?: string; answerId?: string; evidenceId?: string }
  ): string {
    const id = uid();
    setEntries((prev) => [...prev, { id, role: "user", type: "text", text, caption, ...extra }]);
    return id;
  }
  function pushBotInstant(text: string) {
    setEntries((prev) => [...prev, { id: uid(), role: "bot", type: "text", text }]);
  }

  async function sayFinding(payload: Omit<Extract<Entry, { type: "finding" }>, "id" | "role" | "type">) {
    await sleep(500);
    setEntries((prev) => [...prev, { id: uid(), role: "bot", type: "finding", ...payload }]);
  }

  function showTyping() {
    setEntries((prev) => [...prev, { id: uid(), role: "bot", type: "typing" }]);
  }
  function hideTyping() {
    setEntries((prev) => prev.filter((e) => e.type !== "typing"));
  }

  // ===== Conversation flow =====

  async function promptNext(ctl: ControlWithQuestions) {
    const next = ctl.followup_questions.find((q) => !answeredIdsRef.current.has(q.id));
    if (next) {
      await say(next.question_text);
      setActiveQuestion(next);
    } else {
      await completeControl(ctl);
    }
  }

  async function hydratePastControls(allControls: ControlWithQuestions[], currentId: string) {
    for (const c of allControls) {
      if (c.id === currentId) break;
      if (c.followup_questions.length === 0 && c.state !== "skipped") continue;
      pushBotInstant(`Control ${c.control_number}: ${c.title}`);
      if (c.state === "skipped") {
        sayUser(`Skip control ${c.control_number}`);
        greetedControlsRef.current.add(c.id);
        continue;
      }
      for (const q of c.followup_questions) {
        if (q.answer_id) {
          answerControlMapRef.current[q.answer_id] = {
            controlId: c.id,
            controlNumber: c.control_number,
            evidenceExpected: q.evidence_expected,
            expectedDocuments: q.expected_documents,
          };
          pushBotInstant(q.question_text);
          sayUser(
            q.raw_text || capitalize(q.response || ""),
            q.raw_text && q.response ? `interpreted as: ${q.response}` : undefined,
            { questionId: q.id, answerId: q.answer_id ?? undefined }
          );
          if (q.evidence_id && q.evidence_filename) {
            sayUser(`📎 ${q.evidence_filename}`, undefined, { evidenceId: q.evidence_id });
          }
        }
      }
      greetedControlsRef.current.add(c.id);
    }
  }

  async function enterControl(ctl: ControlWithQuestions, isFirst: boolean) {
    setControl(ctl);
    setActiveQuestion(null);
    setActiveEvidence(null);
    controlLockedRef.current = false;
    answeredIdsRef.current = new Set(
      ctl.followup_questions.filter((q) => q.answer_id).map((q) => q.id)
    );

    if (!greetedControlsRef.current.has(ctl.id)) {
      greetedControlsRef.current.add(ctl.id);
      await say(
        isFirst
          ? `Let's get started with control ${ctl.control_number}: "${ctl.title}"`
          : `Great, let's move on to control ${ctl.control_number}: "${ctl.title}"`
      );
    }

    for (const q of ctl.followup_questions) {
      if (q.answer_id) {
        answerControlMapRef.current[q.answer_id] = {
          controlId: ctl.id,
          controlNumber: ctl.control_number,
          evidenceExpected: q.evidence_expected,
          expectedDocuments: q.expected_documents,
        };
        pushBotInstant(q.question_text);
        sayUser(
          q.raw_text || capitalize(q.response || ""),
          q.raw_text && q.response ? `interpreted as: ${q.response}` : undefined,
          { questionId: q.id, answerId: q.answer_id ?? undefined }
        );
      }
    }

    await promptNext(ctl);
  }

  async function completeControl(ctl: ControlWithQuestions) {
    setBusy(true);
    controlLockedRef.current = true;
    await say("Thanks! Let me evaluate this control...");
    showTyping();
    try {
      const result = await api.assessControl(ctl.id);
      hideTyping();
      await sayFinding({
        maturity: result.maturity_level,
        confidence: result.confidence,
        mode: result.assessment_mode,
        finding: result.finding,
        recommendation: result.recommendation,
      });
      await advanceToNextControl();
    } catch {
      hideTyping();
      setError("Could not evaluate this control. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function advanceToNextControl() {
    if (!id) return;
    showTyping();
    try {
      const updatedAssessment = await api.getAssessment(id);
      setAssessment(updatedAssessment);
      let next = await api.getCurrentControl(id);
      hideTyping();
      if (!next) {
        setFinished(true);
        return;
      }
      if (next.followup_questions.length === 0) {
        next = await api.startControl(next.id);
      }
      await enterControl(next, false);
    } catch {
      hideTyping();
      setError("Something went wrong while loading the next control.");
    }
  }

  // ===== Initial load =====

  useEffect(() => {
    if (!id || initializedRef.current) return;
    initializedRef.current = true;

    (async () => {
      try {
        const a = await api.getAssessment(id);
        setAssessment(a);

        let current = await api.getCurrentControl(id);
        if (!current) {
          setFinished(true);
          setLoadingInitial(false);
          return;
        }
        if (current.followup_questions.length === 0) {
          current = await api.startControl(current.id);
        }

        const allControls = await api.listControls(id);

        setLoadingInitial(false);

        const name = fullName;
        const company = companyName;
        await say(
          name
            ? `Hi ${name.split(" ")[0]} 👋 I'm your TISAX assistant.${
                company ? ` I see you're assessing ${company} — let's get started.` : " Let's get started."
              }`
            : "Hi there 👋 I'm your TISAX assistant. Let's get started."
        );
        await say(
          `We'll go through "${a.name}" one control at a time. I'll ask a few questions per control, and you can answer with a quick tap or in your own words.`
        );
        await hydratePastControls(allControls, current.id);
        await enterControl(current, true);
      } catch {
        setError("Could not load this assessment.");
        setLoadingInitial(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // ===== User actions =====

  async function onAnswered(question: FollowupQuestion, res: AnswerResult) {
    answeredIdsRef.current.add(question.id);
    if (question.evidence_expected && res.response !== "no") {
      await say(
        `This can be verified with a document (${
          question.expected_documents.join(", ") || "policy, procedure, record..."
        }). You can upload it now — it's optional, but it improves the reliability of the result.`
      );
      setActiveEvidence({ answerId: res.id, docs: question.expected_documents });
    } else if (controlRef.current) {
      await promptNext(controlRef.current);
    }
  }

  async function handleQuickReply(value: "yes" | "no" | "partial") {
    if (!activeQuestion || busy) return;
    const q = activeQuestion;
    setBusy(true);
    setActiveQuestion(null);
    const entryId = sayUser(capitalize(value));
    try {
      const res = await api.answerQuestion(q.id, { response: value });
      if (controlRef.current) {
        answerControlMapRef.current[res.id] = {
          controlId: controlRef.current.id,
          controlNumber: controlRef.current.control_number,
          evidenceExpected: q.evidence_expected,
          expectedDocuments: q.expected_documents,
        };
      }
      setEntries((prev) =>
        prev.map((e) => (e.id === entryId && e.type === "text" ? { ...e, questionId: q.id, answerId: res.id } : e))
      );
      await onAnswered(q, res);
    } catch {
      setError("Could not save your answer. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSendText() {
    const text = draft.trim();
    if (!activeQuestion || !text || busy) return;
    const q = activeQuestion;
    setBusy(true);
    setActiveQuestion(null);
    const entryId = sayUser(text);
    setDraft("");
    try {
      const res = await api.answerQuestion(q.id, { raw_text: text });
      if (controlRef.current) {
        answerControlMapRef.current[res.id] = {
          controlId: controlRef.current.id,
          controlNumber: controlRef.current.control_number,
          evidenceExpected: q.evidence_expected,
          expectedDocuments: q.expected_documents,
        };
      }
      setEntries((prev) =>
        prev.map((e) => (e.id === entryId && e.type === "text" ? { ...e, questionId: q.id, answerId: res.id } : e))
      );
      await say(`Got it — I'll mark this as "${res.response}".`);
      await onAnswered(q, res);
    } catch {
      setError("Could not save your answer. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(file: File) {
    if (!activeEvidence) return;
    const ev = activeEvidence;
    setActiveEvidence(null);
    setEvidenceUi("uploading");
    try {
      const uploaded = await api.uploadEvidence(ev.answerId, file);
            sayUser(`📎 ${uploaded.filename}`, undefined, { evidenceId: uploaded.id })
      setEvidenceUi("analyzing");
      const analyzed = await api.analyzeEvidence(uploaded.id);
      const verdict = analyzed.analysis?.verdict || "reviewed";
      await say(
        `Document reviewed — ${verdict.replace(/_/g, " ")}.${
          analyzed.analysis?.summary ? " " + analyzed.analysis.summary : ""
        }`
      );
    } catch {
      await say("I couldn't read that file — let's continue without it.");
    } finally {
      setEvidenceUi("idle");
      if (controlRef.current) await promptNext(controlRef.current);
    }
  }

  async function handleSkipEvidence() {
    if (!activeEvidence) return;
    setActiveEvidence(null);
    sayUser("Skip, no document");
    if (controlRef.current) await promptNext(controlRef.current);
  }

  async function handleSkipControl() {
    if (!control || busy) return;
    setBusy(true);
    sayUser(`Skip control ${control.control_number}`);
    try {
      await api.skipControl(control.id);
      await advanceToNextControl();
    } finally {
      setBusy(false);
    }
  }

  // ===== Edit a past or current answer =====

  async function reassessPastControl(controlId: string, controlNumber: string) {
    await say(`You updated your answer for control ${controlNumber}. Let me re-evaluate it...`);
    showTyping();
    try {
      const result = await api.assessControl(controlId);
      hideTyping();
      await sayFinding({
        maturity: result.maturity_level,
        confidence: result.confidence,
        mode: result.assessment_mode,
        finding: `Updated result — ${result.finding}`,
        recommendation: result.recommendation,
      });
    } catch {
      hideTyping();
      await say("I couldn't re-evaluate that control right now — your answer is saved, but the score wasn't updated.");
    }
  }

  async function handleEditAnswer(entryId: string, newValue: string, isFreeText: boolean) {
    const entry = entries.find((e) => e.id === entryId);
    if (!entry || entry.type !== "text" || !entry.answerId) return;
    setBusy(true);
    try {
      const res = await api.editAnswer(entry.answerId, isFreeText ? { raw_text: newValue } : { response: newValue });
      const displayText = isFreeText ? newValue : capitalize(newValue);
      setEntries((prev) =>
        prev.map((e) =>
          e.id === entryId && e.type === "text"
            ? { ...e, text: displayText, caption: isFreeText ? `interpreted as: ${res.response}` : undefined }
            : e
        )
      );
      setEditingEntryId(null);

      const owner = answerControlMapRef.current[entry.answerId];
      const isPastControl = !!owner && owner.controlId !== controlRef.current?.id;

      if (owner?.evidenceExpected && res.response !== "no") {
        // Offer evidence first — reassessment (if this is a past, completed
        // control) happens AFTER the evidence is resolved, so it isn't
        // missed by an evaluation that ran too early.
        setEntries((prev) => [
          ...prev,
          {
            id: uid(),
            role: "bot",
            type: "evidence-request",
            answerId: entry.answerId!,
            docs: owner.expectedDocuments,
            status: "idle",
            controlId: owner.controlId,
            controlNumber: owner.controlNumber,
          },
        ]);
      } else if (isPastControl) {
        await reassessPastControl(owner!.controlId, owner!.controlNumber);
      }
    } catch {
      setError("Could not update your answer. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function handleInlineEvidenceUpload(
    entryId: string,
    answerId: string,
    controlId: string,
    controlNumber: string,
    file: File
  ) {
    setEntries((prev) =>
      prev.map((e) => (e.id === entryId && e.type === "evidence-request" ? { ...e, status: "uploading" } : e))
    );
    try {
      const uploaded = await api.uploadEvidence(answerId, file);
      setEntries((prev) =>
        prev.map((e) => (e.id === entryId && e.type === "evidence-request" ? { ...e, status: "analyzing" } : e))
      );
      const analyzed = await api.analyzeEvidence(uploaded.id);
      const verdict = analyzed.analysis?.verdict || "reviewed";
      setEntries((prev) => prev.filter((e) => e.id !== entryId));
            sayUser(`📎 ${uploaded.filename}`, undefined, { evidenceId: uploaded.id });
      await say(
        `Document reviewed — ${verdict.replace(/_/g, " ")}.${
          analyzed.analysis?.summary ? " " + analyzed.analysis.summary : ""
        }`
      );
    } catch {
      setEntries((prev) =>
        prev.map((e) => (e.id === entryId && e.type === "evidence-request" ? { ...e, status: "idle" } : e))
      );
      return;
    }
    if (controlId !== controlRef.current?.id) {
      await reassessPastControl(controlId, controlNumber);
    }
  }

  async function handleInlineEvidenceSkip(entryId: string, controlId: string, controlNumber: string) {
    setEntries((prev) => prev.filter((e) => e.id !== entryId));
    sayUser("Skip, no document");
    if (controlId !== controlRef.current?.id) {
      await reassessPastControl(controlId, controlNumber);
    }
  }

  const composerDisabled = busy || streaming !== null || (!activeQuestion && !activeEvidence);

  // ===== Render =====

  if (loadingInitial) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="text-slate-400">Loading assessment...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <p className="text-rose-500">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 rounded-lg bg-brand-500 px-5 py-2 text-white"
        >
          Retry
        </button>
      </div>
    );
  }

  if (finished) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-24 text-center">
        <div className="text-5xl">🎉</div>
        <h1 className="mt-4 text-2xl font-bold text-slate-900 dark:text-white">
          Assessment complete
        </h1>
        <p className="mt-2 text-slate-500 dark:text-slate-400">
          All controls have been answered or skipped. View your results on the dashboard.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link
            to={`/assessments/${id}/dashboard`}
            className="rounded-lg bg-brand-500 px-6 py-3 font-semibold text-white hover:bg-brand-600"
          >
            View dashboard
          </Link>
          <Link
            to="/assessments"
            className="rounded-lg border border-slate-300 px-6 py-3 font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200"
          >
            Back to assessments
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col px-4 sm:px-6">
      {/* Header */}
      <div className="shrink-0 border-b border-slate-200 py-3 dark:border-slate-800">
        <div className="flex items-center justify-between text-sm">
          <div>
            <span className="font-semibold text-slate-800 dark:text-slate-100">{assessment?.name}</span>
            {control && <span className="ml-2 text-slate-400">· Control {control.control_number}</span>}
          </div>
          <button
            onClick={handleSkipControl}
            disabled={busy || streaming !== null}
            className="text-xs font-medium text-slate-400 hover:text-slate-600 disabled:opacity-40 dark:hover:text-slate-200"
          >
            Skip this control →
          </button>
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
          <div
            className="h-full rounded-full bg-brand-500 transition-all"
            style={{ width: `${assessment?.progress_percent ?? 0}%` }}
          />
        </div>
      </div>

      {/* Transcript */}
      <div className="flex-1 space-y-3 overflow-y-auto py-4">
        {entries.map((e) =>
          e.type === "evidence-request" ? (
            <InlineEvidenceRequest
              key={e.id}
              entry={e}
              onUpload={(file) => handleInlineEvidenceUpload(e.id, e.answerId, e.controlId, e.controlNumber, file)}
              onSkip={() => handleInlineEvidenceSkip(e.id, e.controlId, e.controlNumber)}
            />
          ) : (
            <ChatBubble
              key={e.id}
              entry={e}
              userInitial={userInitial}
              userPhoto={profilePhoto}
              editable={e.type === "text" && e.role === "user" && !!e.answerId && !controlLockedRef.current}
              isEditing={editingEntryId === e.id}
              onStartEdit={() => setEditingEntryId(e.id)}
              onCancelEdit={() => setEditingEntryId(null)}
              onSaveEdit={(value, isFreeText) => handleEditAnswer(e.id, value, isFreeText)}
              responseScale={assessment?.response_scale}
            />
          )
        )}
        {streaming && (
          <ChatBubble
            entry={{ id: streaming.id, role: "bot", type: "text", text: streaming.shown + "▍" }}
            userInitial={userInitial}
            userPhoto={profilePhoto}
          />
        )}
        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      <div className="shrink-0 border-t border-slate-200 py-4 dark:border-slate-800">
        {activeQuestion && (
          <div className="mb-2 flex flex-wrap gap-2">
            {getQuickReplies(assessment?.response_scale).map((b) => (
              <button
                key={b.value}
                onClick={() => handleQuickReply(b.value)}
                disabled={busy}
                className={`rounded-full px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50 ${b.className}`}
              >
                {b.label}
              </button>
            ))}
          </div>
        )}

        {activeEvidence && (
          <div className="mb-3 flex items-center gap-3">
            <label className="cursor-pointer rounded-lg border border-dashed border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800">
              {evidenceUi === "uploading" ? "Uploading..." : evidenceUi === "analyzing" ? "Analyzing..." : "📎 Upload document"}
              <input
                type="file"
                className="hidden"
                disabled={evidenceUi !== "idle"}
                accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
                onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
              />
            </label>
            <button
              onClick={handleSkipEvidence}
              disabled={evidenceUi !== "idle"}
              className="text-sm text-slate-400 hover:text-slate-600 disabled:opacity-40 dark:hover:text-slate-200"
            >
              Skip, continue without it
            </button>
          </div>
        )}

        <div className="flex gap-2">
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSendText()}
            disabled={composerDisabled}
            placeholder={
              activeQuestion
                ? "Or type your answer..."
                : activeEvidence
                ? "Upload a document or skip above"
                : "TISAX Assist is typing..."
            }
            className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-brand-500 disabled:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-white dark:disabled:bg-slate-800/50"
          />
          <button
            onClick={handleSendText}
            disabled={composerDisabled || !draft.trim()}
            className="rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

// ===== Chat bubble renderer =====

function ChatBubble({
  entry,
  userInitial,
  userPhoto,
  editable,
  isEditing,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  responseScale,
}: {
  entry: Entry;
  userInitial: string;
  userPhoto?: string | null;
  editable?: boolean;
  isEditing?: boolean;
  onStartEdit?: () => void;
  onCancelEdit?: () => void;
  onSaveEdit?: (value: string, isFreeText: boolean) => void;
  responseScale?: string;
}) {
  const [editDraft, setEditDraft] = useState("");

  if (entry.type === "typing") {
    return (
      <div className="flex items-end gap-2">
        <BotAvatar />
        <div className="rounded-2xl rounded-bl-sm bg-slate-100 px-4 py-3 dark:bg-slate-800">
          <span className="flex gap-1">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
          </span>
        </div>
      </div>
    );
  }

  if (entry.type === "finding") {
    return (
      <div className="flex items-end gap-2">
        <BotAvatar />
        <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-brand-200 bg-brand-50 px-4 py-3 text-sm dark:border-brand-500/20 dark:bg-brand-500/5">
          <div className="flex items-center gap-2">
            <span className="rounded bg-brand-500 px-2 py-0.5 text-xs font-bold text-white">
              ML{entry.maturity}
            </span>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {entry.confidence} confidence · {entry.mode}
            </span>
          </div>
          <p className="mt-2 text-slate-700 dark:text-slate-200">{entry.finding}</p>
          <p className="mt-2 text-brand-700 dark:text-brand-400">💡 {entry.recommendation}</p>
        </div>
      </div>
    );
  }

  const isBot = entry.role === "bot";

  if (isEditing) {
    return (
      <div className="flex flex-col items-end gap-2">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm border border-brand-300 bg-white p-3 dark:border-brand-500/40 dark:bg-slate-800">
          <div className="flex flex-wrap gap-2">
            {getQuickReplies(responseScale).map((b) => (
              <button
                key={b.value}
                onClick={() => onSaveEdit?.(b.value, false)}
                className={`rounded-full px-3 py-1 text-xs font-semibold text-white ${b.className}`}
              >
                {b.label}
              </button>
            ))}
          </div>
          <div className="mt-2 flex gap-2">
            <input
              type="text"
              value={editDraft}
              onChange={(e) => setEditDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && editDraft.trim() && onSaveEdit?.(editDraft.trim(), true)}
              placeholder="Type a new answer..."
              autoFocus
              className="flex-1 rounded-lg border border-slate-300 px-2 py-1 text-sm outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            />
            <button
              onClick={onCancelEdit}
              className="rounded-lg px-2 py-1 text-xs text-slate-400 hover:text-slate-600"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex items-end gap-2 ${isBot ? "" : "flex-row-reverse"}`}>
      {isBot ? <BotAvatar /> : <UserAvatar initial={userInitial} photo={userPhoto} />}
      <div className={`max-w-[80%] ${isBot ? "" : "text-right"}`}>
        <div
          className={`inline-block rounded-2xl px-4 py-2.5 text-sm ${
            isBot
              ? "rounded-bl-sm bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100"
              : "rounded-br-sm bg-brand-500 text-white"
          }`}
        >
                    {entry.type === "text" && entry.evidenceId ? (
            <button
              onClick={async () => {
                const blob = await downloadEvidence(entry.evidenceId!);
                window.open(URL.createObjectURL(blob), "_blank");
              }}
              className="underline decoration-dotted hover:opacity-80"
            >
              {entry.text}
            </button>
          ) : (
            entry.text
          )}
        </div>
        {entry.caption && <p className="mt-0.5 text-xs italic text-slate-400">{entry.caption}</p>}
        {editable && (
          <button onClick={onStartEdit} className="mt-0.5 block text-xs text-slate-400 hover:text-brand-500">
            Edit
          </button>
        )}
      </div>
    </div>
  );
}

function InlineEvidenceRequest({
  entry,
  onUpload,
  onSkip,
}: {
  entry: Extract<Entry, { type: "evidence-request" }>;
  onUpload: (file: File) => void;
  onSkip: () => void;
}) {
  return (
    <div className="flex items-end gap-2">
      <BotAvatar />
      <div className="max-w-[85%] rounded-2xl rounded-bl-sm bg-slate-100 px-4 py-3 text-sm dark:bg-slate-800">
        <p className="text-slate-800 dark:text-slate-100">
          Your updated answer could be backed by a document ({entry.docs.join(", ") || "a policy or record"}). Want to upload it?
        </p>
        {entry.status === "idle" && (
          <div className="mt-2 flex items-center gap-3">
            <label className="cursor-pointer rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-xs text-slate-600 hover:bg-white dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700">
              📎 Upload document
              <input
                type="file"
                className="hidden"
                accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
                onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
              />
            </label>
            <button onClick={onSkip} className="text-xs text-slate-400 hover:text-slate-600">
              Skip
            </button>
          </div>
        )}
        {entry.status === "uploading" && <p className="mt-2 text-xs text-slate-400">Uploading...</p>}
        {entry.status === "analyzing" && <p className="mt-2 text-xs text-slate-400">Analyzing...</p>}
      </div>
    </div>
  );
}

function BotAvatar() {
  return (
    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-500 text-xs font-bold text-white">
      T
    </div>
  );
}
function UserAvatar({ initial, photo }: { initial: string; photo?: string | null }) {
  if (photo) {
    return <img src={photo} alt="" className="h-7 w-7 shrink-0 rounded-full object-cover" />;
  }
  return (
    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-300 text-xs font-bold text-slate-700 dark:bg-slate-600 dark:text-slate-100">
      {initial}
    </div>
  );
}