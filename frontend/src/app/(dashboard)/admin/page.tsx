"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import api from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { useRouter } from "next/navigation";
import {
  Users, TrendingUp, Activity, Loader2, Search, Shield,
  UserX, UserCheck, Key, Crown, Send, BarChart3, Clock,
  CheckCircle, XCircle, Globe, Mail,
} from "lucide-react";
import toast from "react-hot-toast";

type Tab = "overview" | "users" | "activity" | "announcements";

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: any; color: string }) {
  return (
    <div className="stat-card">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-muted-foreground">{label}</span>
        <Icon className={`w-4 h-4 ${color}`} />
      </div>
      <div className={`text-3xl font-bold ${color}`}>{value.toLocaleString()}</div>
    </div>
  );
}

export default function AdminPage() {
  const { user } = useAuthStore();
  const router = useRouter();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("overview");
  const [search, setSearch] = useState("");
  const [filterSuspended, setFilterSuspended] = useState<boolean | undefined>(undefined);
  const [announcement, setAnnouncement] = useState({ title: "", message: "" });
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [newPassword, setNewPassword] = useState("");

  // Redirect non-admins
  if (user && user.role !== "admin") {
    router.replace("/dashboard");
    return null;
  }

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: () => api.get("/admin/stats").then((r) => r.data),
  });

  const { data: users = [], isLoading: usersLoading } = useQuery({
    queryKey: ["admin-users", search, filterSuspended],
    queryFn: () => api.get("/admin/users", {
      params: { search: search || undefined, is_suspended: filterSuspended },
    }).then((r) => r.data),
    enabled: tab === "users" || tab === "overview",
  });

  const { data: activity = [] } = useQuery({
    queryKey: ["admin-activity"],
    queryFn: () => api.get("/admin/login-activity").then((r) => r.data),
    enabled: tab === "activity",
  });

  const { data: announcements = [] } = useQuery({
    queryKey: ["admin-announcements"],
    queryFn: () => api.get("/admin/announcements").then((r) => r.data),
    enabled: tab === "announcements",
  });

  const suspendMutation = useMutation({
    mutationFn: (userId: string) => api.post(`/admin/users/${userId}/suspend`, {}),
    onSuccess: () => { toast.success("User suspended"); qc.invalidateQueries({ queryKey: ["admin-users"] }); },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Failed"),
  });

  const reactivateMutation = useMutation({
    mutationFn: (userId: string) => api.post(`/admin/users/${userId}/reactivate`),
    onSuccess: () => { toast.success("User reactivated"); qc.invalidateQueries({ queryKey: ["admin-users"] }); },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Failed"),
  });

  const resetPasswordMutation = useMutation({
    mutationFn: ({ userId, password }: { userId: string; password: string }) =>
      api.post(`/admin/users/${userId}/reset-password`, { new_password: password }),
    onSuccess: () => { toast.success("Password reset"); setSelectedUser(null); setNewPassword(""); },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Failed"),
  });

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.patch(`/admin/users/${userId}/role`, { role }),
    onSuccess: () => { toast.success("Role updated"); qc.invalidateQueries({ queryKey: ["admin-users"] }); },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Failed"),
  });

  const announceMutation = useMutation({
    mutationFn: () => api.post("/admin/announcements", announcement),
    onSuccess: () => {
      toast.success("Announcement sent to all users!");
      setAnnouncement({ title: "", message: "" });
      qc.invalidateQueries({ queryKey: ["admin-announcements"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Failed"),
  });

  const tabs: { id: Tab; label: string; icon: any }[] = [
    { id: "overview", label: "Overview", icon: BarChart3 },
    { id: "users", label: "Users", icon: Users },
    { id: "activity", label: "Login Activity", icon: Clock },
    { id: "announcements", label: "Announcements", icon: Send },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-neon-purple/20 flex items-center justify-center">
          <Shield className="w-5 h-5 text-neon-purple" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Admin Panel</h1>
          <p className="text-muted-foreground text-sm">Platform management & analytics</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-muted/50 p-1 rounded-xl w-fit">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === id ? "bg-card text-foreground shadow" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab === "overview" && (
        <div className="space-y-6">
          {statsLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-neon-green" /></div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard label="Total Users" value={stats?.total_users ?? 0} icon={Users} color="text-neon-green" />
              <StatCard label="Active Users" value={stats?.active_users ?? 0} icon={UserCheck} color="text-neon-blue" />
              <StatCard label="Total Trades" value={stats?.total_trades ?? 0} icon={TrendingUp} color="text-neon-purple" />
              <StatCard label="AI Predictions" value={stats?.total_predictions ?? 0} icon={Activity} color="text-yellow-400" />
              <StatCard label="AI Chats" value={stats?.total_ai_chats ?? 0} icon={BarChart3} color="text-pink-400" />
              <StatCard label="Google Users" value={stats?.google_users ?? 0} icon={Globe} color="text-blue-400" />
              <StatCard label="Verified Users" value={stats?.verified_users ?? 0} icon={CheckCircle} color="text-neon-green" />
              <StatCard label="Suspended" value={stats?.suspended_users ?? 0} icon={UserX} color="text-red-400" />
            </div>
          )}

          {/* Recent users preview */}
          <div className="glass-card">
            <h3 className="font-semibold mb-4">Recent Registrations</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-muted-foreground text-left">
                    <th className="pb-3 font-medium">User</th>
                    <th className="pb-3 font-medium">Plan</th>
                    <th className="pb-3 font-medium">Provider</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Joined</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {users.slice(0, 5).map((u: any) => (
                    <tr key={u.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3">
                        <div className="font-medium">{u.name}</div>
                        <div className="text-xs text-muted-foreground">{u.email}</div>
                      </td>
                      <td className="py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          u.account_type === "pro" ? "bg-neon-green/20 text-neon-green" :
                          u.account_type === "enterprise" ? "bg-neon-purple/20 text-neon-purple" : "bg-muted text-muted-foreground"
                        }`}>{u.account_type}</span>
                      </td>
                      <td className="py-3 text-muted-foreground capitalize">{u.auth_provider}</td>
                      <td className="py-3">
                        {u.is_suspended ? (
                          <span className="text-xs text-red-400 flex items-center gap-1"><XCircle className="w-3 h-3" /> Suspended</span>
                        ) : (
                          <span className="text-xs text-neon-green flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Active</span>
                        )}
                      </td>
                      <td className="py-3 text-muted-foreground">{new Date(u.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Users Tab */}
      {tab === "users" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name or email..."
                className="w-full bg-muted border border-border rounded-lg pl-9 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50"
              />
            </div>
            <select
              value={filterSuspended === undefined ? "" : String(filterSuspended)}
              onChange={(e) => setFilterSuspended(e.target.value === "" ? undefined : e.target.value === "true")}
              className="bg-muted border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none"
            >
              <option value="">All users</option>
              <option value="false">Active only</option>
              <option value="true">Suspended only</option>
            </select>
          </div>

          {usersLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-neon-green" /></div>
          ) : (
            <div className="glass-card overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-muted-foreground text-left">
                    <th className="pb-3 font-medium">User</th>
                    <th className="pb-3 font-medium">Role</th>
                    <th className="pb-3 font-medium">Plan</th>
                    <th className="pb-3 font-medium">Provider</th>
                    <th className="pb-3 font-medium">Verified</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {users.map((u: any) => (
                    <tr key={u.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3">
                        <div className="font-medium">{u.name}</div>
                        <div className="text-xs text-muted-foreground">{u.email}</div>
                      </td>
                      <td className="py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          u.role === "admin" ? "bg-neon-purple/20 text-neon-purple" : "bg-muted text-muted-foreground"
                        }`}>
                          {u.role === "admin" && <Crown className="w-3 h-3 inline mr-1" />}
                          {u.role}
                        </span>
                      </td>
                      <td className="py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs ${
                          u.account_type === "pro" ? "bg-neon-green/20 text-neon-green" :
                          u.account_type === "enterprise" ? "bg-neon-purple/20 text-neon-purple" : "bg-muted text-muted-foreground"
                        }`}>{u.account_type}</span>
                      </td>
                      <td className="py-3 text-muted-foreground capitalize text-xs">{u.auth_provider}</td>
                      <td className="py-3">
                        {u.is_verified
                          ? <CheckCircle className="w-4 h-4 text-neon-green" />
                          : <XCircle className="w-4 h-4 text-muted-foreground" />}
                      </td>
                      <td className="py-3">
                        {u.is_suspended
                          ? <span className="text-xs text-red-400">Suspended</span>
                          : <span className="text-xs text-neon-green">Active</span>}
                      </td>
                      <td className="py-3">
                        <div className="flex items-center gap-1">
                          {u.id !== user?.id && (
                            <>
                              {u.is_suspended ? (
                                <button
                                  onClick={() => reactivateMutation.mutate(u.id)}
                                  title="Reactivate"
                                  className="p-1.5 rounded hover:bg-neon-green/10 text-neon-green transition-colors"
                                >
                                  <UserCheck className="w-4 h-4" />
                                </button>
                              ) : (
                                <button
                                  onClick={() => suspendMutation.mutate(u.id)}
                                  title="Suspend"
                                  className="p-1.5 rounded hover:bg-red-400/10 text-red-400 transition-colors"
                                  disabled={u.role === "admin"}
                                >
                                  <UserX className="w-4 h-4" />
                                </button>
                              )}
                              <button
                                onClick={() => setSelectedUser(u)}
                                title="Reset Password"
                                className="p-1.5 rounded hover:bg-neon-blue/10 text-neon-blue transition-colors"
                              >
                                <Key className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => roleMutation.mutate({ userId: u.id, role: u.role === "admin" ? "user" : "admin" })}
                                title={u.role === "admin" ? "Demote to user" : "Promote to admin"}
                                className="p-1.5 rounded hover:bg-neon-purple/10 text-neon-purple transition-colors"
                              >
                                <Crown className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {users.length === 0 && (
                <p className="text-center text-muted-foreground py-8">No users found</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Login Activity Tab */}
      {tab === "activity" && (
        <div className="glass-card overflow-x-auto">
          <h3 className="font-semibold mb-4">Recent Login Activity</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-muted-foreground text-left">
                <th className="pb-3 font-medium">User ID</th>
                <th className="pb-3 font-medium">Provider</th>
                <th className="pb-3 font-medium">IP Address</th>
                <th className="pb-3 font-medium">Result</th>
                <th className="pb-3 font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {activity.map((a: any) => (
                <tr key={a.id} className="hover:bg-muted/30 transition-colors">
                  <td className="py-3 font-mono text-xs text-muted-foreground">{a.user_id.slice(0, 8)}...</td>
                  <td className="py-3 capitalize text-xs">{a.provider}</td>
                  <td className="py-3 text-muted-foreground text-xs">{a.ip_address || "—"}</td>
                  <td className="py-3">
                    {a.success
                      ? <span className="text-xs text-neon-green flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Success</span>
                      : <span className="text-xs text-red-400 flex items-center gap-1"><XCircle className="w-3 h-3" /> Failed</span>}
                  </td>
                  <td className="py-3 text-muted-foreground text-xs">{new Date(a.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {activity.length === 0 && <p className="text-center text-muted-foreground py-8">No activity yet</p>}
        </div>
      )}

      {/* Announcements Tab */}
      {tab === "announcements" && (
        <div className="space-y-6">
          <div className="glass-card">
            <h3 className="font-semibold mb-4 flex items-center gap-2"><Send className="w-4 h-4 text-neon-green" /> Send Announcement</h3>
            <div className="space-y-3">
              <input
                value={announcement.title}
                onChange={(e) => setAnnouncement({ ...announcement, title: e.target.value })}
                placeholder="Announcement title"
                className="w-full bg-muted border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50"
              />
              <textarea
                value={announcement.message}
                onChange={(e) => setAnnouncement({ ...announcement, message: e.target.value })}
                placeholder="Write your message to all users..."
                rows={4}
                className="w-full bg-muted border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50 resize-none"
              />
              <button
                onClick={() => announceMutation.mutate()}
                disabled={!announcement.title || !announcement.message || announceMutation.isPending}
                className="btn-primary flex items-center gap-2"
              >
                {announceMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                {announceMutation.isPending ? "Sending..." : "Send to All Users"}
              </button>
            </div>
          </div>

          <div className="glass-card">
            <h3 className="font-semibold mb-4">Past Announcements</h3>
            <div className="space-y-3">
              {announcements.map((a: any) => (
                <div key={a.id} className="border border-border rounded-lg p-4">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="font-medium">{a.title}</h4>
                    <span className="text-xs text-muted-foreground whitespace-nowrap">{new Date(a.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">{a.message}</p>
                </div>
              ))}
              {announcements.length === 0 && <p className="text-muted-foreground text-sm">No announcements yet</p>}
            </div>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="glass-card w-full max-w-sm">
            <h3 className="font-semibold mb-1">Reset Password</h3>
            <p className="text-sm text-muted-foreground mb-4">Set a new password for <span className="text-foreground">{selectedUser.email}</span></p>
            <input
              type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
              placeholder="New password (min 8 chars)"
              className="w-full bg-muted border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50 mb-4"
            />
            <div className="flex gap-2">
              <button
                onClick={() => resetPasswordMutation.mutate({ userId: selectedUser.id, password: newPassword })}
                disabled={newPassword.length < 8 || resetPasswordMutation.isPending}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
              >
                {resetPasswordMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                Reset
              </button>
              <button onClick={() => { setSelectedUser(null); setNewPassword(""); }} className="flex-1 bg-muted hover:bg-muted/80 rounded-lg py-2 text-sm transition-colors">
                Cancel
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
