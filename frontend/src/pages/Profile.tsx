import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import * as authApi from "../api/auth";
import type { User } from "../types";
import PhotoCropModal from "../components/PhotoCropModal";

const SECTORS = [
  "Automotive Supplier",
  "OEM / Vehicle Manufacturer",
  "IT Service Provider",
  "Engineering Services",
  "Logistics",
  "Other",
];

const JOB_TITLES = [
  "CEO / Founder",
  "CISO / Information Security Officer",
  "Compliance Manager",
  "Quality Manager",
  "IT Manager / IT Director",
  "Project Manager",
  "Consultant",
  "Other",
];

const COMPANY_SIZES = [
  "1-10 employees",
  "11-50 employees",
  "51-200 employees",
  "201-1000 employees",
  "1000+ employees",
];

const AUDIT_REASONS = [
  "An existing customer requires it",
  "To become an approved supplier / attract new customers",
  "Required for a specific project or tender I'm participating in",
  "Internal decision — proactively improving our security posture",
  "Other",
];

export default function Profile() {
  const { logout, setProfilePhoto: syncProfilePhoto } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [photoBusy, setPhotoBusy] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  // Profile info edit state
  const [editingInfo, setEditingInfo] = useState(false);
  const [savingInfo, setSavingInfo] = useState(false);
  const [infoError, setInfoError] = useState<string | null>(null);
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [sector, setSector] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [companySize, setCompanySize] = useState("");
  const [auditReason, setAuditReason] = useState("");

  async function handlePhotoChange(file: File) {
    setPhotoBusy(true);
    try {
      const updated = await authApi.uploadProfilePhoto(file);
      setUser(updated);
      syncProfilePhoto(updated.profile_photo || null);
    } catch {
      setError("Could not upload photo. Use a PNG, JPEG or WEBP under 5MB.");
    } finally {
      setPhotoBusy(false);
    }
  }

  async function handlePhotoRemove() {
    setPhotoBusy(true);
    try {
      const updated = await authApi.removeProfilePhoto();
      setUser(updated);
      syncProfilePhoto(null);
    } finally {
      setPhotoBusy(false);
    }
  }

  function loadFormFromUser(me: User) {
    setFullName(me.full_name);
    setCompanyName(me.company_name || "");
    setSector(me.sector || "");
    setJobTitle(me.job_title || "");
    setCompanySize(me.company_size || "");
    setAuditReason(me.audit_reason || "");
  }

  useEffect(() => {
    (async () => {
      try {
        const me = await authApi.getMe();
        setUser(me);
        loadFormFromUser(me);
        syncProfilePhoto(me.profile_photo || null);
      } catch {
        setError("Could not load your profile.");
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function startEditingInfo() {
    if (user) loadFormFromUser(user);
    setInfoError(null);
    setEditingInfo(true);
  }

  function cancelEditingInfo() {
    if (user) loadFormFromUser(user);
    setInfoError(null);
    setEditingInfo(false);
  }

  async function handleSaveInfo() {
    if (!fullName.trim()) {
      setInfoError("Full name cannot be empty.");
      return;
    }
    setSavingInfo(true);
    setInfoError(null);
    try {
      const updated = await authApi.updateProfile({
        full_name: fullName.trim(),
        company_name: companyName || null,
        sector: sector || null,
        job_title: jobTitle || null,
        company_size: companySize || null,
        audit_reason: auditReason || null,
      });
      setUser(updated);
      setEditingInfo(false);
    } catch {
      setInfoError("Could not save your changes. Please try again.");
    } finally {
      setSavingInfo(false);
    }
  }

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  if (loading) {
    return <div className="p-16 text-center text-slate-400">Loading profile...</div>;
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Profile & Settings</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Manage your account and preferences.
      </p>

      {error && (
        <div className="mt-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">
          {error}
        </div>
      )}

      {user && (
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-800/50">
          <div className="flex items-center gap-4 border-b border-slate-100 p-6 dark:border-slate-700">
            <div className="relative">
              <label
                className={`flex h-14 w-14 cursor-pointer items-center justify-center overflow-hidden rounded-full bg-brand-500 text-xl font-bold text-white ${
                  photoBusy ? "opacity-50" : ""
                }`}
              >
                {user.profile_photo ? (
                  <img src={user.profile_photo} alt="" className="h-full w-full object-cover" />
                ) : (
                  user.full_name.charAt(0).toUpperCase()
                )}
                <input
                  type="file"
                  className="hidden"
                  accept="image/png,image/jpeg,image/webp"
                  disabled={photoBusy}
                  onChange={(e) => e.target.files?.[0] && setPendingFile(e.target.files[0])}
                />
              </label>
              <span className="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-white text-[10px] shadow dark:bg-slate-700">
                📷
              </span>
            </div>
            <div>
              <p className="font-semibold text-slate-900 dark:text-white">{user.full_name}</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">{user.email}</p>
              {user.profile_photo && (
                <button
                  onClick={handlePhotoRemove}
                  disabled={photoBusy}
                  className="mt-1 text-xs text-slate-400 hover:text-rose-500 disabled:opacity-40"
                >
                  Remove photo
                </button>
              )}
            </div>
          </div>

          <div className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                Your information
              </h2>
              {!editingInfo && (
                <button
                  onClick={startEditingInfo}
                  className="text-xs font-semibold text-brand-600 hover:text-brand-700 dark:text-brand-400"
                >
                  Edit
                </button>
              )}
            </div>

            {infoError && (
              <div className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-500/10 dark:text-red-400">
                {infoError}
              </div>
            )}

            {!editingInfo ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <InfoRow label="Company" value={user.company_name || "Not specified"} />
                <InfoRow label="Sector" value={user.sector || "Not specified"} />
                <InfoRow label="Job title" value={user.job_title || "Not specified"} />
                <InfoRow label="Company size" value={user.company_size || "Not specified"} />
                <InfoRow
                  label="Reason for TISAX assessment"
                  value={user.audit_reason || "Not specified"}
                />
                <InfoRow label="Member since" value={new Date(user.created_at).toLocaleDateString()} />
                <InfoRow label="Account status" value={user.is_active ? "Active" : "Inactive"} />
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300">
                    Full name
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300">
                    Company
                  </label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300">
                    Sector
                  </label>
                  <select
                    value={sector}
                    onChange={(e) => setSector(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  >
                    <option value="">Not specified</option>
                    {SECTORS.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300">
                    Job title
                  </label>
                  <select
                    value={jobTitle}
                    onChange={(e) => setJobTitle(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  >
                    <option value="">Not specified</option>
                    {JOB_TITLES.map((j) => (
                      <option key={j} value={j}>{j}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300">
                    Company size
                  </label>
                  <select
                    value={companySize}
                    onChange={(e) => setCompanySize(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  >
                    <option value="">Not specified</option>
                    {COMPANY_SIZES.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300">
                    Reason for TISAX assessment
                  </label>
                  <select
                    value={auditReason}
                    onChange={(e) => setAuditReason(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  >
                    <option value="">Not specified</option>
                    {AUDIT_REASONS.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={cancelEditingInfo}
                    disabled={savingInfo}
                    className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveInfo}
                    disabled={savingInfo}
                    className="flex-1 rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
                  >
                    {savingInfo ? "Saving..." : "Save changes"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Preferences */}
      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-800/50">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Preferences</h2>
        <div className="mt-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-800 dark:text-slate-100">Dark mode</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Switch between light and dark appearance.
            </p>
          </div>
          <button
            onClick={toggleTheme}
            className={`relative h-7 w-12 rounded-full transition-colors ${
              theme === "dark" ? "bg-brand-500" : "bg-slate-300"
            }`}
          >
            <span
              className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                theme === "dark" ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>
      </div>

      {pendingFile && (
        <PhotoCropModal
          file={pendingFile}
          onCancel={() => setPendingFile(null)}
          onConfirm={(blob) => {
            setPendingFile(null);
            handlePhotoChange(new File([blob], "avatar.jpg", { type: "image/jpeg" }));
          }}
        />
      )}

      {/* Danger zone */}
      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-800/50">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Session</h2>
        <button
          onClick={handleLogout}
          className="mt-4 rounded-lg border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 dark:border-red-500/30 dark:text-red-400 dark:hover:bg-red-500/10"
        >
          Log out
        </button>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-sm text-slate-800 dark:text-slate-100">{value}</p>
    </div>
  );
}