import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import * as authApi from "../api/auth";
import type { User } from "../types";
import PhotoCropModal from "../components/PhotoCropModal";

export default function Profile() {
  const { logout, setProfilePhoto: syncProfilePhoto } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [photoBusy, setPhotoBusy] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

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

  useEffect(() => {
    (async () => {
      try {
        const me = await authApi.getMe();
        setUser(me);
        syncProfilePhoto(me.profile_photo || null);
      } catch {
        setError("Could not load your profile.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

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

          <div className="grid gap-4 p-6 sm:grid-cols-2">
            <InfoRow label="Company" value={user.company_name || "Not specified"} />
            <InfoRow label="Sector" value={user.sector || "Not specified"} />
            <InfoRow
              label="Member since"
              value={new Date(user.created_at).toLocaleDateString()}
            />
            <InfoRow label="Account status" value={user.is_active ? "Active" : "Inactive"} />
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