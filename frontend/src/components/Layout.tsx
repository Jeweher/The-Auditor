import type { ReactNode } from "react";
import { useLocation } from "react-router-dom";
import Navbar from "./Navbar";
import Footer from "./Footer";

export default function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();
  // The chat page manages its own full-height scroll area (like a real
  // chat app), so the site footer and page-level scroll don't apply there.
  const isChatPage = /^\/assessments\/[^/]+\/chat/.test(location.pathname);

  return (
    <div
      className={`flex flex-col bg-white dark:bg-slate-900 ${
        isChatPage ? "h-screen overflow-hidden" : "min-h-screen"
      }`}
    >
      <Navbar />
      <main className={isChatPage ? "flex-1 overflow-hidden" : "flex-1"}>{children}</main>
      {!isChatPage && <Footer />}
    </div>
  );
}