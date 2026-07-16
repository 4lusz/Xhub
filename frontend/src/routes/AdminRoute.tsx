import { Navigate, Outlet } from "react-router-dom";
import { Loader2 } from "lucide-react";

import { useSession } from "@/hooks/useAuth";

export function AdminRoute() {
  const { isAdmin, isLoadingUser } = useSession();

  if (isLoadingUser) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
