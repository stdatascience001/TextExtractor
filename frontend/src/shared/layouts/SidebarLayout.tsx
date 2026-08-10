import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import {
  LayoutDashboard,
  FolderKanban,
  FileText,
  Database,
  Search,
  BarChart3,
  Settings,
  LogOut,
  User as UserIcon,
  Menu,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarLayoutProps {
  children?: React.ReactNode;
}

export const SidebarLayout: React.FC<SidebarLayoutProps> = ({ children }) => {
  const { user, logout, isAuthenticated } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background">
        {children}
      </div>
    );
  }

  const menuItems = [
    { name: "Dashboard", path: "/", icon: LayoutDashboard },
    { name: "Projects", path: "/projects", icon: FolderKanban },
    { name: "Documents", path: "/my-documents", icon: FileText },
    { name: "Knowledge", path: "/knowledge", icon: Database },
    { name: "Search", path: "/search", icon: Search },
    { name: "Reports", path: "/reports", icon: BarChart3 },
    { name: "Settings", path: "/profile", icon: Settings },
  ];

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="hidden md:flex flex-col w-64 border-r border-border bg-card/50 backdrop-blur-xl">
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-border">
          <div className="w-8 h-8 flex items-center justify-center bg-primary/10 rounded-lg">
            <img src="/favicon1.png" alt="Logo" className="w-6 h-6 object-contain" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-foreground leading-none">DocExtract</h1>
            <span className="text-[10px] text-muted-foreground">Knowledge Engine</span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {menuItems.map((item) => {
            const isActive =
              item.path === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.path);

            return (
              <Link
                key={item.name}
                to={item.path}
                className={cn(
                  "flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <item.icon className="w-4 h-4" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* User Account / Footer */}
        <div className="p-4 border-t border-border bg-card/30">
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg bg-muted/35 mb-2">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary text-xs font-semibold uppercase">
              {user?.username?.substring(0, 2) || "US"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-foreground truncate">{user?.username || "Guest User"}</p>
              <p className="text-[10px] text-muted-foreground truncate">{user?.email || "guest@example.com"}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-4 py-2 rounded-lg text-xs font-medium text-red-500 hover:bg-red-50/10 hover:text-red-600 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile Header */}
        <header className="flex md:hidden items-center justify-between px-6 py-4 border-b border-border bg-card">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 flex items-center justify-center bg-primary/10 rounded-lg">
              <img src="/favicon1.png" alt="Logo" className="w-6 h-6 object-contain" />
            </div>
            <h1 className="text-sm font-semibold text-foreground">DocExtract</h1>
          </div>
          <button className="p-2 rounded-md hover:bg-muted text-muted-foreground">
            <Menu className="w-5 h-5" />
          </button>
        </header>

        {/* Page Body */}
        <main className="flex-1 overflow-y-auto bg-background/95">
          <div className="container max-w-[110rem] mx-auto px-6 py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
export default SidebarLayout;
