import { Outlet } from "react-router-dom";

import { MobileSidebar, Sidebar } from "@/components/layout/Sidebar";
import { UserMenu } from "@/components/layout/UserMenu";
import { useOAuthCallbackFeedback } from "@/hooks/useOAuthCallbackFeedback";

export function DashboardLayout() {
  useOAuthCallbackFeedback();

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center justify-between gap-2 border-b border-border px-4 sm:px-8 md:justify-end">
          <MobileSidebar />
          <UserMenu />
        </header>
        <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-8 sm:py-8">
          <div className="mx-auto w-full max-w-6xl animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
