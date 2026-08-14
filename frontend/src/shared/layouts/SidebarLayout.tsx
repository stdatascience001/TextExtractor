import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Tooltip } from "@/components/ui/Tooltip";
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
  Sun,
  Moon,
  Monitor,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "next-themes";

interface SidebarLayoutProps {
  children?: React.ReactNode;
}

export const SidebarLayout: React.FC<SidebarLayoutProps> = ({ children }) => {
  const { user, logout, isAuthenticated } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();

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
    { name: "Settings", path: "/settings", icon: Settings },
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
                <h1 className="text-sm font-semibold text-foreground leading-none">DocLens</h1>
                <span className="text-[10px] text-muted-foreground">Knowledge Engine</span>
              </div>
            )}
          </div>

          <Tooltip content={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"} description={isCollapsed ? "Show navigation labels" : "Hide navigation labels"} position="right">
            <button
              onClick={toggleSidebar}
              className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors duration-200"
            >
              {isCollapsed ? (
                <PanelLeftOpen className="w-4 h-4" />
              ) : (
                <PanelLeftClose className="w-4 h-4" />
              )}
            </button>
          </Tooltip>
        </div>

        {/* Navigation Items */}
        <nav className={cn("flex-1 py-6 space-y-1 transition-all duration-300", isCollapsed ? "px-2 overflow-visible" : "px-4 overflow-y-auto")}>
          {menuItems.map((item) => {
            const isActive =
              item.path === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.path);

            const sidebarTooltipDescription = {
              "Dashboard": "View metrics, upload documents, and track parsing history.",
              "Projects": "Organize your documents, members, and custom vector search contexts.",
              "Documents": "Access, filter, and delete all extracted files.",
              "Knowledge": "Verify, edit, or reject structured facts extracted from your documents.",
              "Search": "Search through raw document content and parsed text.",
              "Reports": "Review usage analytics, counts, and extraction patterns.",
              "Settings": "Configure your account details, preferences, and security."
            }[item.name] || `Go to ${item.name}`;

            const linkElement = (
              <Link
                to={item.path}
                className={cn(
                  "flex items-center rounded-lg text-sm font-medium transition-all duration-200 group relative",
                  isCollapsed ? "justify-center p-2.5" : "gap-3 px-4 py-2.5",
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <item.icon className="w-4 h-4 flex-shrink-0" />
                {!isCollapsed && <span className="transition-all duration-200 whitespace-nowrap">{item.name}</span>}
              </Link>
            );

            return (
              <React.Fragment key={item.name}>
                {isCollapsed ? (
                  <Tooltip content={item.name} description={sidebarTooltipDescription} position="right">
                    {linkElement}
                  </Tooltip>
                ) : (
                  linkElement
                )}
              </React.Fragment>
            );
          })}
        </nav>

        {/* User Account / Footer */}
        <div className={cn("border-t border-border bg-card/30 transition-all duration-300", isCollapsed ? "p-2" : "p-4")}>
          {(() => {
            const userCardElement = (
              <Link
                to="/profile"
                className={cn(
                  "flex items-center rounded-lg bg-muted/35 hover:bg-muted/65 mb-2 transition-all duration-300 group relative border border-transparent hover:border-border/35",
                  isCollapsed ? "justify-center p-2" : "gap-3 px-2 py-2"
                )}
              >
                <div className="w-8 h-8 rounded-full bg-primary/20 flex-shrink-0 flex items-center justify-center text-primary text-xs font-semibold uppercase group-hover:scale-105 transition-transform duration-300">
                  {user?.username?.substring(0, 2) || "US"}
                </div>
                {!isCollapsed && (
                  <div className="flex-1 min-w-0 transition-all duration-200">
                    <p className="text-xs font-semibold text-foreground truncate group-hover:text-primary transition-colors">{user?.username || "Guest User"}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{user?.email || "guest@example.com"}</p>
                  </div>
                )}
              </Link>
            );

            const signOutElement = (
              <button
                onClick={handleLogout}
                className={cn(
                  "flex items-center rounded-lg text-xs font-medium text-red-500 hover:bg-red-50/10 hover:text-red-600 transition-colors group relative",
                  isCollapsed ? "justify-center p-2.5 w-full" : "gap-3 px-4 py-2 w-full"
                )}
              >
                <LogOut className="w-3.5 h-3.5 flex-shrink-0" />
                {!isCollapsed && <span>Sign Out</span>}
              </button>
            );

            const themeToggleElement = (
              <div className={cn(
                "flex items-center gap-1 mb-2 bg-muted/20 p-1 rounded-lg border border-border/20 transition-all duration-300",
                isCollapsed ? "flex-col p-1 border-none bg-transparent animate-fade-in" : "flex-row justify-between animate-fade-in"
              )}>
                {isCollapsed ? (
                  <Tooltip content="Toggle Theme" description={`Active: ${theme || "system"}`} position="right">
                    <button
                      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                      className="w-8 h-8 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground flex items-center justify-center transition-all duration-200 border border-border/30 bg-muted/40"
                    >
                      <Sun className="w-4 h-4 dark:hidden text-amber-500 animate-pulse-soft" />
                      <Moon className="w-4 h-4 hidden dark:block text-blue-400 animate-pulse-soft" />
                    </button>
                  </Tooltip>
                ) : (
                  <>
                    <Tooltip content="Light Theme" description="Switch to light interface" position="right">
                      <button
                        onClick={() => setTheme("light")}
                        className={cn(
                          "flex-1 py-1 rounded-md flex items-center justify-center gap-1 transition-all duration-200 text-[9px] font-bold uppercase tracking-wider",
                          theme === "light"
                            ? "bg-background text-primary shadow-sm border border-border/50"
                            : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
                        )}
                      >
                        <Sun className="w-3.5 h-3.5 text-amber-500" />
                        <span>Light</span>
                      </button>
                    </Tooltip>
                    <Tooltip content="Dark Theme" description="Switch to dark interface" position="right">
                      <button
                        onClick={() => setTheme("dark")}
                        className={cn(
                          "flex-1 py-1 rounded-md flex items-center justify-center gap-1 transition-all duration-200 text-[9px] font-bold uppercase tracking-wider",
                          theme === "dark"
                            ? "bg-background text-primary shadow-sm border border-border/50"
                            : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
                        )}
                      >
                        <Moon className="w-3.5 h-3.5 text-blue-400" />
                        <span>Dark</span>
                      </button>
                    </Tooltip>
                    <Tooltip content="System Preference" description="Follow your OS style settings" position="right">
                      <button
                        onClick={() => setTheme("system")}
                        className={cn(
                          "flex-1 py-1 rounded-md flex items-center justify-center gap-1 transition-all duration-200 text-[9px] font-bold uppercase tracking-wider",
                          theme === "system"
                            ? "bg-background text-primary shadow-sm border border-border/50"
                            : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
                        )}
                      >
                        <Monitor className="w-3.5 h-3.5 text-slate-400" />
                        <span>Sys</span>
                      </button>
                    </Tooltip>
                  </>
                )}
              </div>
            );

            return (
              <>
                {themeToggleElement}
                {isCollapsed ? (
                  <Tooltip content={user?.username || "Guest User"} description={user?.email || "guest@example.com"} position="right">
                    {userCardElement}
                  </Tooltip>
                ) : (
                  userCardElement
                )}

                {isCollapsed ? (
                  <Tooltip content="Sign Out" description="Sign out of your active session." position="right">
                    {signOutElement}
                  </Tooltip>
                ) : (
                  signOutElement
                )}
              </>
            );
          })()}
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
            <h1 className="text-sm font-semibold text-foreground">DocLens</h1>
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
