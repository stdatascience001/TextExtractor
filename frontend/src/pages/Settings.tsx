import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { useToast } from "../components/ui/use-toast";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "../components/ui/alert-dialog";
import { motion } from "framer-motion";
import { Lock, Trash2, Loader2, Save, Sun, Moon, Monitor, Settings as SettingsIcon, Eye, EyeOff } from "lucide-react";
import { SidebarLayout } from "@/shared/layouts/SidebarLayout";
import { useTheme } from "next-themes";
import { Tooltip } from "@/components/ui/Tooltip";

export default function Settings() {
  const { logout, isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { theme, setTheme } = useTheme();

  const [loading, setLoading] = useState(true);
  const [profileData, setProfileData] = useState<any>(null);

  // Form states
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (isAuthLoading) return;
    
    if (!isAuthenticated) {
      navigate("/login");
      return;
    }
    fetchProfile();
  }, [isAuthenticated, isAuthLoading, navigate]);

  const fetchProfile = async () => {
    try {
      const data = await api.getProfile();
      setProfileData(data);
    } catch (err: any) {
      toast({ variant: "destructive", title: "Error", description: err.message || "Failed to load settings" });
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdatingPassword(true);
    try {
      await api.changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      toast({ title: "Success", description: "Password changed successfully." });
    } catch (err: any) {
      toast({ variant: "destructive", title: "Password Change Failed", description: err.message });
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    try {
      await api.deleteAccount();
      toast({ title: "Account Deleted", description: "Your account and all data have been permanently removed." });
      logout();
      navigate("/");
    } catch (err: any) {
      toast({ variant: "destructive", title: "Deletion Failed", description: err.message });
      setIsDeleting(false);
    }
  };

  if (loading || isAuthLoading) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  return (
    <SidebarLayout>
      <div className="space-y-6 max-w-4xl">
        <div className="flex items-center gap-3">
          <SettingsIcon className="w-8 h-8 text-primary animate-spin" style={{ animationDuration: "10s" }} />
          <div>
            <h1 className="text-3xl font-bold text-foreground">Settings</h1>
            <p className="text-sm text-muted-foreground">Manage your account preferences, theme, and security settings</p>
          </div>
        </div>

        {/* Theme Settings Section */}
        <motion.section
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="bg-card border border-border p-6 rounded-2xl shadow-sm relative overflow-hidden"
        >
          {/* Subtle gradient glow decoration */}
          <div className="absolute -top-24 -right-24 w-48 h-48 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
          
          <div className="flex items-center gap-3 mb-6 relative z-10">
            <Sun className="w-5 h-5 text-primary dark:hidden animate-pulse-soft" />
            <Moon className="w-5 h-5 text-primary hidden dark:block animate-pulse-soft" />
            <h2 className="text-xl font-bold text-foreground">Theme Settings</h2>
          </div>
          <p className="text-sm text-muted-foreground mb-6 relative z-10 max-w-xl">
            Customize the look and feel of your workspace. Choose between light, dark, or system default themes.
          </p>
          <div className="grid grid-cols-3 gap-4 max-w-md relative z-10">
            <Tooltip content="Light Mode" description="Switch to clean, light workspace colors">
              <button
                type="button"
                onClick={() => setTheme("light")}
                className={`w-full flex flex-col items-center justify-center p-5 rounded-xl border-2 transition-all duration-300 relative group overflow-hidden ${
                  theme === "light"
                    ? "bg-primary/[0.06] border-primary text-primary shadow-soft scale-[1.02]"
                    : "bg-background border-border text-muted-foreground hover:bg-muted/40 hover:text-foreground hover:border-border/80"
                }`}
              >
                {theme === "light" && (
                  <div className="absolute inset-0 bg-gradient-to-tr from-primary/5 to-transparent pointer-events-none" />
                )}
                <Sun className={`w-6 h-6 mb-3 transition-transform duration-300 group-hover:scale-110 ${theme === "light" ? "text-primary" : "text-muted-foreground"}`} />
                <span className="text-xs font-bold uppercase tracking-wider">Light</span>
              </button>
            </Tooltip>

            <Tooltip content="Dark Mode" description="Switch to dark, eyes-friendly workspace colors">
              <button
                type="button"
                onClick={() => setTheme("dark")}
                className={`w-full flex flex-col items-center justify-center p-5 rounded-xl border-2 transition-all duration-300 relative group overflow-hidden ${
                  theme === "dark"
                    ? "bg-primary/[0.06] border-primary text-primary shadow-soft scale-[1.02]"
                    : "bg-background border-border text-muted-foreground hover:bg-muted/40 hover:text-foreground hover:border-border/80"
                }`}
              >
                {theme === "dark" && (
                  <div className="absolute inset-0 bg-gradient-to-tr from-primary/5 to-transparent pointer-events-none" />
                )}
                <Moon className={`w-6 h-6 mb-3 transition-transform duration-300 group-hover:scale-110 ${theme === "dark" ? "text-primary" : "text-muted-foreground"}`} />
                <span className="text-xs font-bold uppercase tracking-wider">Dark</span>
              </button>
            </Tooltip>

            <Tooltip content="System Preference" description="Sync theme with your OS system preferences">
              <button
                type="button"
                onClick={() => setTheme("system")}
                className={`w-full flex flex-col items-center justify-center p-5 rounded-xl border-2 transition-all duration-300 relative group overflow-hidden ${
                  theme === "system"
                    ? "bg-primary/[0.06] border-primary text-primary shadow-soft scale-[1.02]"
                    : "bg-background border-border text-muted-foreground hover:bg-muted/40 hover:text-foreground hover:border-border/80"
                }`}
              >
                {theme === "system" && (
                  <div className="absolute inset-0 bg-gradient-to-tr from-primary/5 to-transparent pointer-events-none" />
                )}
                <Monitor className={`w-6 h-6 mb-3 transition-transform duration-300 group-hover:scale-110 ${theme === "system" ? "text-primary" : "text-muted-foreground"}`} />
                <span className="text-xs font-bold uppercase tracking-wider">System</span>
              </button>
            </Tooltip>
          </div>
        </motion.section>

        {/* Password Update Section */}
        <motion.section
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="bg-card border border-border p-6 rounded-2xl shadow-sm"
        >
          <div className="flex items-center gap-3 mb-6">
            <Lock className="w-5 h-5 text-primary" />
            <h2 className="text-xl font-bold text-foreground">Change Password</h2>
          </div>
          <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Current Password</label>
              <div className="relative">
                <input
                  type={showCurrentPassword ? "text" : "password"}
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full p-2.5 pr-10 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1 rounded-md hover:bg-muted/50 transition-colors"
                  aria-label={showCurrentPassword ? "Hide password" : "Show password"}
                >
                  {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">New Password</label>
              <div className="relative">
                <input
                  type={showNewPassword ? "text" : "password"}
                  required
                  minLength={6}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full p-2.5 pr-10 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1 rounded-md hover:bg-muted/50 transition-colors"
                  aria-label={showNewPassword ? "Hide password" : "Show password"}
                >
                  {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <Tooltip content="Update Password" description="Save new password to your account">
              <button
                type="submit"
                disabled={isUpdatingPassword || !currentPassword || !newPassword}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isUpdatingPassword ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Update Password
              </button>
            </Tooltip>
          </form>
        </motion.section>

        {/* Danger Zone */}
        <motion.section
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="border border-destructive/30 bg-destructive/5 p-6 rounded-2xl shadow-sm"
        >
          <div className="flex items-center gap-3 mb-2">
            <Trash2 className="w-5 h-5 text-destructive" />
            <h2 className="text-xl font-bold text-destructive">Danger Zone</h2>
          </div>
          <p className="text-sm text-muted-foreground mb-6">
            Permanently delete your account and all associated documents. This action is irreversible.
          </p>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <button
                disabled={isDeleting}
                className="px-4 py-2 bg-destructive text-destructive-foreground rounded-lg text-sm font-medium hover:bg-destructive/90 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <div className="flex items-center gap-2">
                  {isDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                  Delete Account
                </div>
              </button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will permanently erase ALL your saved documents and data. This action CANNOT be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel className="bg-transparent border border-input hover:bg-slate-100 hover:text-slate-900 transition-colors">Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDeleteAccount}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  Yes, delete my account
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </motion.section>
      </div>
    </SidebarLayout>
  );
}
