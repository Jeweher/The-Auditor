import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import * as assessmentsApi from "../api/assessments";
import type { Assessment } from "../types";
import axios from "axios";

const AL_OPTIONS = [
  { value: "AL1", label: "AL1 — Low protection needs" },
  { value: "AL2", label: "AL2 — High protection needs" },
  { value: "AL3", label: "AL3 — Very high protection needs" },
];

const TARGET_OPTIONS = [
  { value: 3, label: "ML3 — Established (standard TISAX target)" },
  { value: 4, label: "ML4 — Predictable (requires measurement evidence)" },
  { value: 5, label: "ML5 — Optimizing (requires improvement evidence)" },
];

const DOMAIN_OPTIONS = [
  { value: "", label: "All domains" },
  { value: "IS", label: "Information Security" },
  { value: "PP", label: "Prototype Protection" },
  { value: "DP", label: "Data Protection" },
];

const EVIDENCE_MODE_OPTIONS = [
  { value: "with_evidence", label: "Standard — with evidence (recommended)" },
  { value: "no_evidence", label: "Declarative only — no evidence" },
];

const RESPONSE_SCALE_OPTIONS = [
  { value: "yes_no_partial", label: "Yes / No / Partially (recommended)" },
  { value: "yes_no", label: "Yes / No only" },
];

const SAMPLE_PERCENT_OPTIONS = [
  { value: "", label: "All controls (100%) — full catalogue" },
  { value: "10", label: "10% of controls" },
  { value: "20", label: "20% of controls" },
  { value: "30", label: "30% of controls" },
  { value: "40", label: "40% of controls" },
  { value: "50", label: "50% of controls" },
  { value: "60", label: "60% of controls" },
  { value: "70", label: "70% of controls" },
  { value: "80", label: "80% of controls" },
  { value: "90", label: "90% of controls" },
];

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    in_progress: "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400",
    completed: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400",
  };
  const label: Record<string, string> = {
    in_progress: "In progress",
    completed: "Completed",
  };
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${styles[status] || "bg-slate-100 text-slate-600"}`}>
      {label[status] || status}
    </span>
  );
}

type UploadStatus = "idle" | "uploading" | "done" | "error";

export default function Assessments() {
  const navigate = useNavigate();
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  // Create form state
  const [name, setName] = useState("");
  const [al, setAl] = useState("AL1");
  const [target, setTarget] = useState(3);
  const [domain, setDomain] = useState("");
  const [evidenceMode, setEvidenceMode] = useState("with_evidence");
  const [responseScale, setResponseScale] = useState("yes_no_partial");
  const [samplePercent, setSamplePercent] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Custom knowledge base upload state
  const [useCustomKb, setUseCustomKb] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedCollection, setUploadedCollection] = useState<string | null>(null);
  const [uploadedInfo, setUploadedInfo] = useState<{ filename: string; chunks: number } | null>(null);

  async function loadAssessments() {
    setLoading(true);
    try {
      const data = await assessmentsApi.listAssessments();
      setAssessments(data);
    } catch {
      // Non-fatal: leave the list empty; the empty state below invites creation.
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAssessments();
  }, []);

  function resetUploadState() {
    setUseCustomKb(false);
    setUploadFile(null);
    setUploadStatus("idle");
    setUploadError(null);
    setUploadedCollection(null);
    setUploadedInfo(null);
  }

  function resetOptionsState() {
    setEvidenceMode("with_evidence");
    setResponseScale("yes_no_partial");
    setSamplePercent("");
  }

  function closeModal() {
    setShowModal(false);
    setCreateError(null);
    resetUploadState();
    resetOptionsState();
  }

  async function handleProcessFile() {
    if (!uploadFile) return;
    setUploadStatus("uploading");
    setUploadError(null);
    try {
      const result = await assessmentsApi.uploadQuestionnaire(uploadFile);
      setUploadedCollection(result.collection);
      setUploadedInfo({ filename: result.filename, chunks: result.chunks_ingested });
      setUploadStatus("done");
    } catch (err) {
      setUploadStatus("error");
      if (axios.isAxiosError(err)) {
        setUploadError(err.response?.data?.message || err.response?.data?.detail || "Could not process this file.");
      } else {
        setUploadError("Something went wrong while processing the file.");
      }
    }
  }

  function handleDiscardUpload() {
    setUploadFile(null);
    setUploadStatus("idle");
    setUploadError(null);
    setUploadedCollection(null);
    setUploadedInfo(null);
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreateError(null);
    setCreating(true);
    try {
      const created = await assessmentsApi.createAssessment({
        name,
        assessment_level: al,
        target_maturity_level: target,
        domain: domain || null,
        kb_collection: useCustomKb && uploadedCollection ? uploadedCollection : null,
        evidence_mode: evidenceMode,
        
        response_scale: responseScale,
        sample_percent: samplePercent ? Number(samplePercent) : null,
        kb_source_filename: useCustomKb && uploadedInfo ? uploadedInfo.filename : null,
      });
      setShowModal(false);
      setName("");
      resetUploadState();
      resetOptionsState();
      navigate(`/assessments/${created.id}/chat`);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setCreateError(err.response?.data?.message || err.response?.data?.detail || "Could not create assessment.");
      } else {
        setCreateError("Something went wrong.");
      }
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this assessment? This cannot be undone.")) return;
    await assessmentsApi.deleteAssessment(id);
    setAssessments((prev) => prev.filter((a) => a.id !== id));
  }

  const createDisabled = creating || uploadStatus === "uploading" || (useCustomKb && uploadStatus !== "done");

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Your assessments
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Track and continue your TISAX self-assessments.
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-600"
        >
          + New assessment
        </button>
      </div>

      {/* List */}
      {loading ? (
        <div className="mt-10 text-center text-slate-400">Loading...</div>
      ) : assessments.length === 0 ? (
        <div className="mt-16 rounded-2xl border border-dashed border-slate-300 p-16 text-center dark:border-slate-700">
          <p className="text-lg font-medium text-slate-700 dark:text-slate-200">
            No assessments yet
          </p>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Create your first assessment to start the AI-guided interview.
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="mt-6 rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-600"
          >
            + New assessment
          </button>
        </div>
      ) : (
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {assessments.map((a) => (
            <div
              key={a.id}
              className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-800/50"
            >
              <div className="flex items-start justify-between">
                <h3 className="font-semibold text-slate-900 dark:text-white">{a.name}</h3>
                <StatusBadge status={a.status} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-700">{a.assessment_level}</span>
                <span className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-700">Target ML{a.target_maturity_level}</span>
                {a.evidence_mode === "no_evidence" && (
                  <span className="rounded bg-amber-100 px-2 py-1 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
                    No evidence
                  </span>
                )}
                {a.response_scale === "yes_no" && (
                  <span className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-700">Yes/No only</span>
                )}
                {a.sample_percent && (
                  <span className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-700">{a.sample_percent}% sample</span>
                )}
                {a.kb_source_filename && (
                  <span className="rounded bg-brand-100 px-2 py-1 text-brand-700 dark:bg-brand-500/10 dark:text-brand-400">
                    📄 {a.kb_source_filename}
                  </span>
                )}
              </div>

              <div className="mt-4">
                <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
                  <span>Progress</span>
                  <span>{a.progress_percent}%</span>
                </div>
                <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
                  <div
                    className="h-full rounded-full bg-brand-500"
                    style={{ width: `${a.progress_percent}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  {a.completed_controls}/{a.total_controls} controls · {a.skipped_controls} skipped
                </p>
              </div>

              <div className="mt-5 flex gap-2">
                <button
                  onClick={() => navigate(`/assessments/${a.id}/chat`)}
                  className="flex-1 rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600"
                >
                  Continue
                </button>
                <button
                  onClick={() => navigate(`/assessments/${a.id}/dashboard`)}
                  className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700"
                >
                  Dashboard
                </button>
                <button
                  onClick={() => handleDelete(a.id)}
                  className="rounded-lg border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:border-red-500/30 dark:text-red-400 dark:hover:bg-red-500/10"
                  aria-label="Delete assessment"
                >
                  🗑
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-2xl bg-white p-6 dark:bg-slate-800">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              New assessment
            </h2>

            {createError && (
              <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">
                {createError}
              </div>
            )}

            {/* Custom knowledge base upload (optional) */}
            <div className="mt-4 rounded-xl border border-slate-200 p-4 dark:border-slate-700">
              <label className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  checked={useCustomKb}
                  onChange={(e) => {
                    setUseCustomKb(e.target.checked);
                    if (!e.target.checked) handleDiscardUpload();
                  }}
                  className="mt-0.5 h-4 w-4 accent-brand-500"
                />
                <div>
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                    Use my own VDA ISA questionnaire
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    By default, The Auditor uses the official VDA ISA 6.0.3 control catalogue
                    (ISA6_EN_6.0.3). Optionally, upload a .xlsx file to base this assessment on
                    your own control catalogue instead.
                  </p>
                </div>
              </label>

              {useCustomKb && (
                <div className="mt-3 space-y-3">
                  {uploadStatus !== "done" && (
                    <>
                      <input
                        type="file"
                        accept=".xlsx"
                        disabled={uploadStatus === "uploading"}
                        onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                        className="block w-full text-xs text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-brand-700 hover:file:bg-brand-100 dark:text-slate-300 dark:file:bg-brand-500/10 dark:file:text-brand-400"
                      />
                      <button
                        type="button"
                        onClick={handleProcessFile}
                        disabled={!uploadFile || uploadStatus === "uploading"}
                        className="w-full rounded-lg border border-brand-300 px-3 py-2 text-xs font-semibold text-brand-700 hover:bg-brand-50 disabled:opacity-40 dark:border-brand-500/40 dark:text-brand-400 dark:hover:bg-brand-500/10"
                      >
                        {uploadStatus === "uploading" ? "Processing your file..." : "Process this file"}
                      </button>
                      {uploadStatus === "uploading" && (
                        <div>
                          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
                            <div className="h-full w-1/3 animate-pulse rounded-full bg-brand-500" />
                          </div>
                          <p className="mt-1 text-xs text-slate-400">
                            Parsing, chunking, and indexing your document — this can take up to 2 minutes. Please don't close this window.
                          </p>
                        </div>
                      )}
                      {uploadStatus === "error" && uploadError && (
                        <p className="text-xs text-rose-500">{uploadError}</p>
                      )}
                    </>
                  )}

                  {uploadStatus === "done" && uploadedInfo && (
                    <div className="flex items-center justify-between rounded-lg bg-emerald-50 px-3 py-2 text-xs dark:bg-emerald-500/10">
                      <span className="text-emerald-700 dark:text-emerald-400">
                        ✓ {uploadedInfo.filename} — {uploadedInfo.chunks} chunks indexed
                      </span>
                      <button
                        type="button"
                        onClick={handleDiscardUpload}
                        className="font-medium text-slate-500 hover:text-slate-700 dark:text-slate-400"
                      >
                        Remove
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            <form onSubmit={handleCreate} className="mt-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Q3 2026 TISAX Assessment"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Assessment Level
                </label>
                <select
                  value={al}
                  onChange={(e) => setAl(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                >
                  {AL_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Target maturity level
                </label>
                <select
                  value={target}
                  onChange={(e) => setTarget(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                >
                  {TARGET_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Domain
                </label>
                <select
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                >
                  {DOMAIN_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              {/* Assessment options — evidence, answer scale, sampling */}
              <div className="space-y-4 rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                  Assessment options
                </p>

                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Evidence requirement
                  </label>
                  <select
                    value={evidenceMode}
                    onChange={(e) => setEvidenceMode(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  >
                    {EVIDENCE_MODE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {evidenceMode === "no_evidence"
                      ? "You will only answer questions — no documents will be requested, and evidence is never taken into account when calculating your maturity level."
                      : "You may be asked to upload supporting documents (policies, records, screenshots) for certain answers. Skipping requested evidence lowers your maturity score for that control."}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Answer scale
                  </label>
                  <select
                    value={responseScale}
                    onChange={(e) => setResponseScale(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  >
                    {RESPONSE_SCALE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {responseScale === "yes_no"
                      ? "Simple, binary answers — no middle ground. Best for a strict, clear-cut assessment."
                      : "Allows nuanced answers — useful when a requirement is only partly implemented."}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Control sampling
                  </label>
                  <select
                    value={samplePercent}
                    onChange={(e) => setSamplePercent(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  >
                    {SAMPLE_PERCENT_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    By default, your assessment covers every control in the catalogue (~80
                    controls). Choosing a lower percentage randomly selects that share of
                    controls instead — for example, 20% randomly includes about 16 out of 80
                    controls, for a quicker, representative assessment rather than a full audit.
                  </p>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createDisabled}
                  className="flex-1 rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Create"}
                </button>
              </div>
              {useCustomKb && uploadStatus !== "done" && (
                <p className="text-center text-xs text-slate-400">
                  Process your file above before creating the assessment.
                </p>
              )}
            </form>
          </div>
        </div>
      )}
    </div>
  );
}