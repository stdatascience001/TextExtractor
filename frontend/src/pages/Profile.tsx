import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { useToast } from "../components/ui/use-toast";
import { motion } from "framer-motion";
import { User as UserIcon, Loader2, Save, ArrowRight, Settings as SettingsIcon } from "lucide-react";
import { format } from "date-fns";
import { SidebarLayout } from "@/shared/layouts/SidebarLayout";
import { Tooltip } from "@/components/ui/Tooltip";

export default function Profile() {
  const { user, isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [profileData, setProfileData] = useState<any>(null);

  // Form states
  const [username, setUsername] = useState("");
  const [isUpdatingUsername, setIsUpdatingUsername] = useState(false);

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
    } catch (err: any) {
      toast({ variant: "destructive", title: "Update Failed", description: err.message });
    } finally {
      setIsUpdatingUsername(false);
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
          <img src="/favicon1.png" alt="Loading..." className="w-10 h-10 animate-spin" />
        </div>
      </div>
    );
  }

  // Generate a random-like theme color based on username initials for the avatar background
  const initials = user?.username?.substring(0, 2).toUpperCase() || "US";

  return (
    <SidebarLayout>
      <div className="space-y-6 max-w-4xl">
        {/* Profile Header Card */}
        <motion.div
          initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }}
          className="relative bg-card border border-border p-6 rounded-2xl shadow-sm overflow-hidden flex flex-col md:flex-row items-center gap-6"
        >
          {/* Decorative background glow */}
          <div className="absolute -bottom-24 -left-24 w-52 h-52 bg-primary/5 rounded-full blur-3xl pointer-events-none" />

          <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-primary to-accent flex items-center justify-center text-white text-2xl font-black shadow-glow z-10 shrink-0 select-none">
            {initials}
          </div>
          <div className="flex-1 text-center md:text-left z-10">
            <h1 className="text-3xl font-black text-foreground tracking-tight">{profileData?.username || "User Profile"}</h1>
            <p className="text-sm text-muted-foreground mt-1 font-medium">{profileData?.email || "Email unavailable"}</p>
            <div className="mt-3 flex flex-wrap justify-center md:justify-start gap-2">
              <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/10 rounded-md">
                Active Member
              </span>
            </div>
          </div>
          <div className="z-10 mt-4 md:mt-0">
            <Tooltip content="Go to Settings" description="Configure theme, password, or delete account">
              <Link
                to="/settings"
                className="px-4 py-2 border border-border bg-background text-foreground hover:bg-muted text-sm font-semibold rounded-xl transition-all duration-300 flex items-center gap-2 shadow-sm"
              >
                <SettingsIcon className="w-4 h-4" />
                <span>Account Settings</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </Tooltip>
          </div>
        </motion.div>

        {/* Statistics Section */}
        <motion.section
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
          className="bg-card border border-border p-6 rounded-2xl shadow-sm"
        >
          <h2 className="text-xl font-bold text-foreground mb-6">Overview & Usage</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-4 bg-muted/40 rounded-xl border border-border/50">
              <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">Member Since</div>
              <div className="text-xl font-extrabold text-foreground">
                {profileData?.created_at ? format(new Date(profileData.created_at), "MMMM yyyy") : "Unknown"}
              </div>
            </div>
            <div className="p-4 bg-muted/40 rounded-xl border border-border/50">
              <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">Total Documents</div>
              <div className="text-xl font-extrabold text-foreground">
                {profileData?.total_documents || 0}
              </div>
            </div>
            <div className="p-4 bg-muted/40 rounded-xl border border-border/50">
              <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">Storage Used</div>
              <div className="text-xl font-extrabold text-foreground">
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
            <Tooltip content="Save Changes" description="Save your updated username">
              <button
                type="submit"
                disabled={isUpdatingUsername || username === profileData?.username}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isUpdatingUsername ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save Changes
              </button>
            </Tooltip>
          </form>
        </motion.section>
      </div>
    </SidebarLayout>
  );
}
