import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
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
import { LogoutButton } from "../components/LogoutButton";
import { motion } from "framer-motion";
import { User as UserIcon, Lock, Trash2, ArrowLeft, Loader2, Save } from "lucide-react";
import { format } from "date-fns";
import { SidebarLayout } from "@/shared/layouts/SidebarLayout";

export default function Profile() {
  const { user, logout, isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [profileData, setProfileData] = useState<any>(null);

  // Form states
  const [username, setUsername] = useState("");
  const [isUpdatingUsername, setIsUpdatingUsername] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
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
      setUsername(data.username);
    } catch (err: any) {
      toast({ variant: "destructive", title: "Error", description: err.message || "Failed to load profile" });
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateUsername = async (e: React.FormEvent) => {
    e.preventDefault();
    if (username === profileData?.username) return;

    setIsUpdatingUsername(true);
    try {
      await api.updateUsername(username);
      setProfileData({ ...profileData, username });
      toast({ title: "Success", description: "Username updated successfully." });
      // The context will update on next reload or we could update it manually, 
      // but for this simple app, it's fine.
    } catch (err: any) {
      toast({ variant: "destructive", title: "Update Failed", description: err.message });
    } finally {
      setIsUpdatingUsername(false);
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

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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
      <div className="space-y-6">

        {/* Statistics Section */}
        <motion.section
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="bg-card border border-border p-6 rounded-2xl shadow-sm"
        >
          <h2 className="text-xl font-bold text-foreground mb-6">Overview</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-4 bg-muted/50 rounded-xl">
              <div className="text-sm text-muted-foreground mb-1">Member Since</div>
              <div className="text-lg font-semibold text-foreground">
                {profileData?.created_at ? format(new Date(profileData.created_at), "MMMM yyyy") : "Unknown"}
              </div>
            </div>
            <div className="p-4 bg-muted/50 rounded-xl">
              <div className="text-sm text-muted-foreground mb-1">Total Documents</div>
              <div className="text-lg font-semibold text-foreground">
                {profileData?.total_documents || 0}
              </div>
            </div>
            <div className="p-4 bg-muted/50 rounded-xl">
              <div className="text-sm text-muted-foreground mb-1">Storage Used</div>
              <div className="text-lg font-semibold text-foreground">
                {formatBytes(profileData?.storage_used_bytes || 0)}
              </div>
            </div>
          </div>
        </motion.section>

        {/* Profile Update Section */}
        <motion.section
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="bg-card border border-border p-6 rounded-2xl shadow-sm"
        >
          <div className="flex items-center gap-3 mb-6">
            <UserIcon className="w-5 h-5 text-primary" />
            <h2 className="text-xl font-bold text-foreground">Profile Information</h2>
          </div>
          <form onSubmit={handleUpdateUsername} className="space-y-4 max-w-md">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Email (Read Only)</label>
              <input
                type="email"
                disabled
                value={profileData?.email || ""}
                className="w-full p-2.5 rounded-lg border border-input bg-muted/50 text-muted-foreground cursor-not-allowed outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Username</label>
              <input
                type="text"
                required
                minLength={2}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
              />
            </div>
            <button
                type="submit"
                disabled={isUpdatingUsername || username === profileData?.username}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isUpdatingUsername ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save Changes
              </button>
          </form>
        </motion.section>

        {/* Password Update Section */}
        <motion.section
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="bg-card border border-border p-6 rounded-2xl shadow-sm"
        >
          <div className="flex items-center gap-3 mb-6">
            <Lock className="w-5 h-5 text-primary" />
            <h2 className="text-xl font-bold text-foreground">Change Password</h2>
          </div>
          <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Current Password</label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">New Password</label>
              <input
                type="password"
                required
                minLength={6}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
              />
            </div>
            <button
                type="submit"
                disabled={isUpdatingPassword || !currentPassword || !newPassword}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isUpdatingPassword ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Update Password
              </button>
          </form>
        </motion.section>

        {/* Danger Zone */}
        <motion.section
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
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
                {/* Delete button content */}
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
