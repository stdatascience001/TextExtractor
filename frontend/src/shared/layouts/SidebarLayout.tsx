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
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarLayoutProps {
  children?: React.ReactNode;
}

export const SidebarLayout: React.FC<SidebarLayoutProps> = ({ children }) => {
  const { user, logout, isAuthenticated } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [isCollapsed, setIsCollapsed] = React.useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("sidebar-collapsed") === "true";
    }
    return false;
  });

  const toggleSidebar = () => {
    setIsCollapsed((prev) => {
      const newVal = !prev;
      localStorage.setItem("sidebar-collapsed", String(newVal));
      return newVal;
    });
  };

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
      <aside className={cn(
        "hidden md:flex flex-col border-r border-border bg-card/50 backdrop-blur-xl transition-all duration-300 ease-in-out flex-shrink-0",
        isCollapsed ? "w-16" : "w-64"
      )}>
        {/* Brand Header */}
        <div className={cn(
          "flex items-center border-b border-border transition-all duration-300 py-5",
          isCollapsed ? "flex-col gap-4 px-2 justify-center" : "px-6 justify-between"
        )}>
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-8 h-8 flex-shrink-0 flex items-center justify-center bg-primary/10 rounded-lg">
              <img src="/favicon1.png" alt="Logo" className="w-6 h-6 object-contain" />
            </div>
            {!isCollapsed && (
              <div className="transition-all duration-300 whitespace-nowrap">
                <h1 className="text-sm font-semibold text-foreground leading-none">DocExtract</h1>
                <span className="text-[10px] text-muted-foreground">Knowledge Engine</span>
              </div>
            )}
          </div>

          <button
            onClick={toggleSidebar}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors duration-200"
            title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {isCollapsed ? (
              <PanelLeftOpen className="w-4 h-4" />
            ) : (
              <PanelLeftClose className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation Items */}
        <nav className={cn("flex-1 py-6 space-y-1 transition-all duration-300", isCollapsed ? "px-2 overflow-visible" : "px-4 overflow-y-auto")}>
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
                  "flex items-center rounded-lg text-sm font-medium transition-all duration-200 group relative",
                  isCollapsed ? "justify-center p-2.5" : "gap-3 px-4 py-2.5",
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
                title={isCollapsed ? item.name : undefined}
              >
                <item.icon className="w-4 h-4 flex-shrink-0" />
                {!isCollapsed && <span className="transition-all duration-200 whitespace-nowrap">{item.name}</span>}

                {/* Premium hover tooltip for collapsed state */}
                {isCollapsed && (
                  <span className="absolute left-14 bg-popover text-popover-foreground text-xs font-semibold px-2.5 py-1.5 rounded-md border border-border shadow-md opacity-0 scale-95 group-hover:opacity-100 group-hover:scale-100 pointer-events-none transition-all duration-150 z-50 whitespace-nowrap">
                    {item.name}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User Account / Footer */}
        <div className={cn("border-t border-border bg-card/30 transition-all duration-300", isCollapsed ? "p-2" : "p-4")}>
          <div className={cn(
            "flex items-center rounded-lg bg-muted/35 mb-2 transition-all duration-300 group relative",
            isCollapsed ? "justify-center p-2" : "gap-3 px-2 py-2"
          )}>
            <div className="w-8 h-8 rounded-full bg-primary/20 flex-shrink-0 flex items-center justify-center text-primary text-xs font-semibold uppercase">
              {user?.username?.substring(0, 2) || "US"}
            </div>
            {!isCollapsed && (
              <div className="flex-1 min-w-0 transition-all duration-200">
                <p className="text-xs font-semibold text-foreground truncate">{user?.username || "Guest User"}</p>
                <p className="text-[10px] text-muted-foreground truncate">{user?.email || "guest@example.com"}</p>
              </div>
            )}

            {/* Hover details for collapsed user */}
            {isCollapsed && (
              <div className="absolute left-14 bg-popover text-popover-foreground text-xs font-semibold p-2.5 rounded-md border border-border shadow-md opacity-0 scale-95 group-hover:opacity-100 group-hover:scale-100 pointer-events-none transition-all duration-150 z-50 whitespace-nowrap flex flex-col gap-0.5">
                <p className="font-semibold text-foreground">{user?.username || "Guest User"}</p>
                <p className="text-[10px] text-muted-foreground font-normal">{user?.email || "guest@example.com"}</p>
              </div>
            )}
          </div>
          <button
            onClick={handleLogout}
            className={cn(
              "flex items-center rounded-lg text-xs font-medium text-red-500 hover:bg-red-50/10 hover:text-red-600 transition-colors group relative",
              isCollapsed ? "justify-center p-2.5 w-full" : "gap-3 px-4 py-2 w-full"
            )}
            title={isCollapsed ? "Sign Out" : undefined}
          >
            <LogOut className="w-3.5 h-3.5 flex-shrink-0" />
            {!isCollapsed && <span>Sign Out</span>}

            {/* Tooltip for Sign Out in collapsed state */}
            {isCollapsed && (
              <span className="absolute left-14 bg-popover text-red-600 text-xs font-semibold px-2.5 py-1.5 rounded-md border border-border shadow-md opacity-0 scale-95 group-hover:opacity-100 group-hover:scale-100 pointer-events-none transition-all duration-150 z-50 whitespace-nowrap">
                Sign Out
              </span>
            )}
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
