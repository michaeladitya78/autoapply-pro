"use client";
import { useState, useEffect, useCallback } from "react";
import { useAuth, UserButton, useUser } from "@clerk/nextjs";
import CareerOpsTab from "./CareerOpsTab";
import { OutreachTab, AnalyticsTab, SettingsTab } from "./DashboardTabs";
import Link from "next/link";
import {
  Bot, LayoutDashboard, Briefcase, Mail, Shield,
  AlertTriangle, BarChart3, Settings, ChevronRight,
  Play, Pause, RefreshCw, Zap, TrendingUp,
  CheckCircle2, XCircle, Clock, Eye, ArrowRight,
  Target, Download, X, ExternalLink,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, AreaChart, Area, XAxis, YAxis } from "recharts";
import { format } from "date-fns";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

const NAV_ITEMS = [
  { icon: LayoutDashboard, label: "Overview", id: "overview" },
  { icon: Briefcase, label: "Applications", id: "applications" },
  { icon: Target, label: "Career-Ops", id: "career-ops" },
  { icon: Mail, label: "Outreach", id: "outreach" },
  { icon: Shield, label: "Accounts", id: "accounts" },
  { icon: AlertTriangle, label: "Flags", id: "flags" },
  { icon: BarChart3, label: "Analytics", id: "analytics" },
  { icon: Settings, label: "Settings", id: "settings" },
];

const STATUS_CONFIG: Record<string, { label: string; color: string; className: string }> = {
  applied: { label: "Applied", color: "#818CF8", className: "badge-applied" },
  viewed: { label: "Viewed", color: "#60A5FA", className: "badge-viewed" },
  interview: { label: "Interview", color: "#34D399", className: "badge-interview" },
  rejected: { label: "Rejected", color: "#F87171", className: "badge-rejected" },
  offer: { label: "Offer!", color: "#FBBF24", className: "badge-offer" },
};

export default function DashboardClient({ userId }: { userId: string }) {
  const { getToken } = useAuth();
  const { user } = useUser();
  const [activeTab, setActiveTab] = useState("overview");
  const [stats, setStats] = useState<any>(null);
  const [applications, setApplications] = useState<any[]>([]);
  const [activityFeed, setActivityFeed] = useState<any[]>([]);
  const [outreachContacts, setOutreachContacts] = useState<any[]>([]);
  const [outreachEmails, setOutreachEmails] = useState<any[]>([]);
  const [flags, setFlags] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [agentStatus, setAgentStatus] = useState<string>("idle");
  const [loading, setLoading] = useState(true);
  const [agentLoading, setAgentLoading] = useState(false);
  const [isNewUser, setIsNewUser] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const fetchWithAuth = useCallback(async (endpoint: string) => {
    const token = await getToken();
    const res = await fetch(`${API}${endpoint}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  }, [getToken]);

  const loadDashboard = useCallback(async () => {
    try {
      const [st, apps, feed, fl, accts, agStatus] = await Promise.all([
        fetchWithAuth("/api/dashboard/stats"),
        fetchWithAuth("/api/applications?limit=50"),
        fetchWithAuth("/api/dashboard/activity-feed?limit=15"),
        fetchWithAuth("/api/flags?status=pending"),
        fetchWithAuth("/api/accounts"),
        fetchWithAuth("/api/agent/status"),
      ]);
      setStats(st);
      setApplications(apps);
      setActivityFeed(feed);
      setFlags(fl);
      setAccounts(accts);
      setAgentStatus(agStatus.status);
      setApiError(null);
      // Detect new user: no applications and no resume
      if (!apps?.length && !st?.resume_uploaded) setIsNewUser(true);
    } catch (err: any) {
      console.error("Dashboard load error:", err);
      setApiError("Could not reach the AutoApply backend. Is it running on port 8080?");
    } finally {
      setLoading(false);
    }
  }, [fetchWithAuth]);

  const loadOutreach = useCallback(async () => {
    try {
      const [contacts, emails] = await Promise.all([
        fetchWithAuth("/api/outreach/contacts"),
        fetchWithAuth("/api/outreach/emails"),
      ]);
      setOutreachContacts(contacts);
      setOutreachEmails(emails);
    } catch { /* silent on outreach load fail */ }
  }, [fetchWithAuth]);

  useEffect(() => {
    loadDashboard();
    const poll = setInterval(loadDashboard, 15000);
    return () => clearInterval(poll);
  }, [loadDashboard]);

  // WebSocket for real-time updates
  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
    if (!wsUrl) return;
    let ws: WebSocket;
    try {
      ws = new WebSocket(`${wsUrl}/ws/${userId}`);
    } catch { return; }
    const ping = setInterval(() => ws.readyState === WebSocket.OPEN && ws.send("ping"), 25000);
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "application_submitted") {
          setActivityFeed(prev => [{ type: "application_submitted", details: msg.payload, timestamp: new Date().toISOString() }, ...prev.slice(0, 29)]);
          loadDashboard();
        } else if (msg.type === "human_flag") {
          setFlags(prev => [{ ...msg.payload, id: Date.now(), created_at: new Date().toISOString() }, ...prev]);
        }
      } catch { /* ignore malformed WS frames */ }
    };
    ws.onerror = () => console.warn("AutoApply WebSocket disconnected — real-time updates paused");
    return () => { clearInterval(ping); try { ws.close(); } catch {} };
  }, [userId, loadDashboard]);

  useEffect(() => {
    if (activeTab === "outreach") loadOutreach();
  }, [activeTab, loadOutreach]);

  const toggleAgent = async () => {
    setAgentLoading(true);
    try {
      const token = await getToken();
      const endpoint = agentStatus === "running" ? "/api/agent/pause" : "/api/agent/start";
      await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ run_type: "full" }),
      });
      await loadDashboard();
    } catch (err) {
      console.error("Agent toggle error:", err);
    } finally {
      setAgentLoading(false);
    }
  };

  const chartData = stats ? [
    { name: "Applied", value: stats.applications?.by_status?.applied || 0 },
    { name: "Viewed", value: stats.applications?.by_status?.viewed || 0 },
    { name: "Interview", value: stats.applications?.by_status?.interview || 0 },
    { name: "Offer", value: stats.applications?.by_status?.offer || 0 },
    { name: "Rejected", value: stats.applications?.by_status?.rejected || 0 },
  ] : [];

  const weeklyData = stats?.weekly_trend || [];

  const COLORS = ["#818CF8", "#60A5FA", "#34D399", "#FBBF24", "#F87171"];

  // Free tier: 20 apps/month limit
  const FREE_APP_LIMIT = 20;
  const FREE_EMAIL_LIMIT = 5;
  const totalApps = stats?.applications?.total || 0;
  const isFreeUser = !stats?.plan || stats.plan === "free";
  const nearLimit = isFreeUser && totalApps >= FREE_APP_LIMIT * 0.8;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/20 mx-auto flex items-center justify-center shimmer" />
          <p className="text-white/40">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      <div className="bg-mesh" />

      {/* Sidebar */}
      <aside className="relative z-10 w-64 shrink-0 glass border-r border-white/08 rounded-none flex flex-col py-6 px-4">
        <div className="flex items-center gap-2 px-2 mb-8">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
            <Bot size={18} className="text-white" />
          </div>
          <span className="font-bold tracking-tight">AutoApply Pro</span>
        </div>

        {/* Agent toggle */}
        <div className={`glass p-4 mb-6 rounded-xl border ${agentStatus === "running" ? "border-green-500/30 glow-green" : "border-white/08"}`}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium">Agent Status</span>
            <div className={`flex items-center gap-1.5 text-xs font-semibold ${agentStatus === "running" ? "text-green-400" : "text-white/40"}`}>
              <span className={`w-2 h-2 rounded-full ${agentStatus === "running" ? "bg-green-400 pulse-dot" : "bg-white/20"}`} />
              {agentStatus === "running" ? "LIVE" : agentStatus.toUpperCase()}
            </div>
          </div>
          <button onClick={toggleAgent} disabled={agentLoading}
            className={`w-full flex items-center justify-center gap-2 py-2.5 text-sm font-semibold rounded-lg transition-all ${agentStatus === "running" ? "bg-orange-500/20 text-orange-400 hover:bg-orange-500/30 border border-orange-500/30" : "btn-primary"}`}>
            {agentLoading ? <RefreshCw size={15} className="animate-spin" /> : agentStatus === "running" ? <Pause size={15} /> : <Play size={15} />}
            {agentLoading ? "Loading..." : agentStatus === "running" ? "Pause Agent" : "Start Agent"}
          </button>
        </div>

        {/* Flags badge */}
        {flags.length > 0 && (
          <div className="flex items-center gap-2 p-3 mb-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 text-sm">
            <AlertTriangle size={15} />
            <span>{flags.length} flag{flags.length > 1 ? "s" : ""} need attention</span>
          </div>
        )}

        <nav className="flex-1 space-y-1">
          {NAV_ITEMS.map(item => (
            <button key={item.id} onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${activeTab === item.id ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/20" : "text-white/50 hover:text-white hover:bg-white/05"}`}>
              <item.icon size={17} />
              {item.label}
              {item.id === "flags" && flags.length > 0 && (
                <span className="ml-auto px-1.5 py-0.5 text-xs bg-amber-500 text-black rounded-full font-bold">{flags.length}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="border-t border-white/08 pt-4 flex items-center gap-3 px-2">
          <UserButton />
          <div className="text-sm">
            <p className="font-medium">My Account</p>
            <p className="text-white/40 text-xs">Free Plan</p>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="relative z-10 flex-1 overflow-auto p-8">
        {/* Backend offline warning */}
        {apiError && (
          <div className="mb-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
            <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-300">Backend offline</p>
              <p className="text-xs text-white/50 mt-0.5">{apiError}</p>
            </div>
          </div>
        )}

        {/* New user onboarding nudge */}
        {isNewUser && activeTab === "overview" && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-5 rounded-xl border border-indigo-500/30 bg-indigo-500/08 flex items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-lg bg-indigo-500/20 flex items-center justify-center shrink-0">
                <Bot size={18} className="text-indigo-400" />
              </div>
              <div>
                <p className="font-semibold text-sm">Welcome! Let's get your agent running ⚡</p>
                <p className="text-xs text-white/45 mt-0.5">Upload your resume, set job preferences, and connect your first platform — takes 3 minutes.</p>
              </div>
            </div>
            <Link href="/onboarding">
              <button className="btn-primary text-sm px-5 py-2.5 flex items-center gap-2 shrink-0">
                Start Setup <ArrowRight size={15} />
              </button>
            </Link>
          </motion.div>
        )}

        {/* Free tier limit warning */}
        {nearLimit && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 rounded-xl border border-amber-500/30 bg-amber-500/08 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <AlertTriangle size={16} className="text-amber-400 shrink-0" />
              <p className="text-sm text-amber-200">
                You've used <strong>{totalApps}/{FREE_APP_LIMIT}</strong> free applications this month.
                Upgrade to Pro for unlimited.
              </p>
            </div>
            <Link href="/pricing">
              <button className="text-xs font-bold px-4 py-2 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30 transition-colors shrink-0">
                Upgrade →
              </button>
            </Link>
          </motion.div>
        )}

        <AnimatePresence mode="wait">
          {activeTab === "overview" && (
            <motion.div key="overview" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <OverviewTab stats={stats} chartData={chartData} weeklyData={weeklyData} colors={COLORS} activityFeed={activityFeed} />
            </motion.div>
          )}
          {activeTab === "applications" && (
            <motion.div key="applications" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <ApplicationsTab applications={applications} />
            </motion.div>
          )}
          {activeTab === "accounts" && (
            <motion.div key="accounts" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <AccountsTab accounts={accounts} />
            </motion.div>
          )}
          {activeTab === "flags" && (
            <motion.div key="flags" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <FlagsTab flags={flags} />
            </motion.div>
          )}
          {activeTab === "outreach" && (
            <motion.div key="outreach" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <OutreachTab contacts={outreachContacts} emails={outreachEmails} />
            </motion.div>
          )}
          {activeTab === "analytics" && (
            <motion.div key="analytics" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <AnalyticsTab stats={stats} chartData={chartData} weeklyData={weeklyData} colors={COLORS} applications={applications} />
            </motion.div>
          )}
          {activeTab === "career-ops" && (
            <motion.div key="career-ops" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <CareerOpsTab getToken={getToken} userId={userId} />
            </motion.div>
          )}
          {activeTab === "settings" && (
            <motion.div key="settings" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <SettingsTab user={user} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

function OverviewTab({ stats, chartData, weeklyData, colors, activityFeed }: any) {
  const metrics = [
    { label: "Total Applications", value: stats?.applications?.total ?? 0, icon: Briefcase, color: "text-indigo-400", bg: "bg-indigo-500/10" },
    { label: "This Week", value: stats?.applications?.this_week ?? 0, icon: TrendingUp, color: "text-emerald-400", bg: "bg-emerald-500/10" },
    { label: "Interview Rate", value: `${stats?.applications?.interview_rate ?? 0}%`, icon: Zap, color: "text-amber-400", bg: "bg-amber-500/10" },
    { label: "Email Response Rate", value: `${stats?.outreach?.response_rate ?? 0}%`, icon: Mail, color: "text-blue-400", bg: "bg-blue-500/10" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Overview</h1>
          <p className="text-white/40 text-sm mt-1">Your agent's performance at a glance</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-white/40">
          <RefreshCw size={14} />
          Updates every 15s
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map(m => (
          <div key={m.label} className="glass p-5 rounded-xl">
            <div className={`w-10 h-10 ${m.bg} rounded-lg flex items-center justify-center mb-4`}>
              <m.icon size={20} className={m.color} />
            </div>
            <div className="text-3xl font-black mb-1">{m.value}</div>
            <div className="text-sm text-white/45">{m.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Funnel chart */}
        <div className="glass p-6 rounded-xl">
          <h3 className="font-semibold mb-5">Application Funnel</h3>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={chartData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, value }) => `${name}: ${value}`} labelLine={false}>
                  {chartData.map((_: any, i: number) => <Cell key={i} fill={colors[i % colors.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "#0D1220", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-white/30 text-sm">No applications yet</div>
          )}
        </div>

        {/* Activity feed */}
        <div className="glass p-6 rounded-xl">
          <h3 className="font-semibold mb-4">Live Agent Activity</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {activityFeed.length === 0 ? (
              <p className="text-white/30 text-sm text-center py-8">Agent hasn't run yet. Start it from the sidebar!</p>
            ) : activityFeed.map((action: any, i: number) => (
              <div key={action.id || i} className="flex items-start gap-3 py-2 border-b border-white/05 last:border-0">
                <div className={`w-2 h-2 mt-2 rounded-full shrink-0 ${action.requires_human ? "bg-amber-400" : "bg-indigo-400"}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white/80 truncate">
                    {action.type?.replace(/_/g, " ")}
                    {action.details?.company && ` — ${action.details.company}`}
                  </p>
                  <p className="text-xs text-white/35 mt-0.5">{action.platform} · {action.timestamp ? format(new Date(action.timestamp), "HH:mm:ss") : ""}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ApplicationsTab({ applications }: { applications: any[] }) {
  const [filter, setFilter] = useState<string>("all");
  const [platformFilter, setPlatformFilter] = useState<string>("all");
  const [selected, setSelected] = useState<any | null>(null);

  const platforms = ["all", ...Array.from(new Set(applications.map(a => a.platform).filter(Boolean)))];
  const filtered = applications
    .filter(a => filter === "all" || a.status === filter)
    .filter(a => platformFilter === "all" || a.platform === platformFilter);

  const exportCSV = () => {
    const headers = ["Company", "Role", "Platform", "Status", "Applied At", "URL"];
    const rows = filtered.map(a => [
      a.company, a.title, a.platform, a.status,
      a.applied_at ? format(new Date(a.applied_at), "yyyy-MM-dd HH:mm") : "",
      a.job_url || "",
    ]);
    const csv = [headers, ...rows].map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "applications.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Applications</h1>
        <button onClick={exportCSV} className="btn-ghost py-2 px-4 text-sm flex items-center gap-2">
          <Download size={14} /> Export CSV
        </button>
      </div>

      {/* Status filter */}
      <div className="flex gap-2 flex-wrap">
        {["all", "applied", "viewed", "interview", "offer", "rejected"].map(s => (
          <button key={s} onClick={() => setFilter(s)}
            className={`px-4 py-2 text-sm rounded-lg border transition-all ${filter === s ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-300" : "border-white/10 text-white/50 hover:border-white/20"}`}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Platform filter */}
      {platforms.length > 2 && (
        <div className="flex gap-2 flex-wrap">
          {platforms.map(p => (
            <button key={p} onClick={() => setPlatformFilter(p)}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-all capitalize ${platformFilter === p ? "bg-blue-500/20 border-blue-500/40 text-blue-300" : "border-white/08 text-white/40 hover:border-white/20"}`}>
              {p}
            </button>
          ))}
        </div>
      )}

      <div className="glass rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/08">
              {["Company", "Role", "Platform", "Status", "Applied"].map(h => (
                <th key={h} className="text-left py-3 px-4 text-xs font-semibold text-white/40 uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr><td colSpan={5} className="text-center py-12 text-white/30">No applications found</td></tr>
            ) : filtered.map(app => (
              <tr key={app.id}
                onClick={() => setSelected(app)}
                className="border-b border-white/05 hover:bg-white/03 transition-colors cursor-pointer">
                <td className="py-3 px-4 font-medium text-sm">{app.company}</td>
                <td className="py-3 px-4 text-sm text-white/70">{app.title}</td>
                <td className="py-3 px-4 text-sm text-white/50 capitalize">{app.platform}</td>
                <td className="py-3 px-4">
                  <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${STATUS_CONFIG[app.status]?.className || "badge-applied"}`}>
                    {STATUS_CONFIG[app.status]?.label || app.status}
                  </span>
                </td>
                <td className="py-3 px-4 text-xs text-white/40">{app.applied_at ? format(new Date(app.applied_at), "MMM d, HH:mm") : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Detail side panel */}
      <AnimatePresence>
        {selected && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-end"
            onClick={() => setSelected(null)}>
            <motion.div initial={{ x: 400 }} animate={{ x: 0 }} exit={{ x: 400 }}
              transition={{ type: "spring", damping: 25 }}
              className="h-full w-full max-w-md glass border-l border-white/10 p-8 overflow-y-auto space-y-5"
              onClick={e => e.stopPropagation()}>
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-bold">{selected.company}</h2>
                  <p className="text-white/60 text-sm mt-0.5">{selected.title}</p>
                </div>
                <button onClick={() => setSelected(null)} className="text-white/30 hover:text-white transition-colors">
                  <X size={20} />
                </button>
              </div>
              <div className="space-y-3">
                {[
                  ["Platform", selected.platform],
                  ["Status", selected.status],
                  ["Applied", selected.applied_at ? format(new Date(selected.applied_at), "MMM d yyyy, HH:mm") : "Unknown"],
                  ["Location", selected.location || "Not specified"],
                  ["Salary", selected.salary_range || "Not listed"],
                ].map(([label, val]) => (
                  <div key={label} className="flex justify-between py-2 border-b border-white/05">
                    <span className="text-sm text-white/40">{label}</span>
                    <span className="text-sm capitalize">{val}</span>
                  </div>
                ))}
              </div>
              {selected.job_url && (
                <a href={selected.job_url} target="_blank" rel="noopener noreferrer"
                  className="btn-ghost w-full py-2.5 text-sm flex items-center justify-center gap-2">
                  View Original Posting <ExternalLink size={14} />
                </a>
              )}
              {selected.cover_letter && (
                <div>
                  <h3 className="text-sm font-semibold mb-2 text-white/60">Cover Letter Used</h3>
                  <p className="text-xs text-white/50 leading-relaxed whitespace-pre-wrap">{selected.cover_letter}</p>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function AccountsTab({ accounts }: { accounts: any[] }) {
  const PLATFORMS = ["linkedin", "indeed", "naukri", "glassdoor", "wellfound", "dice", "ziprecruiter"];
  const DAILY_LIMITS: Record<string, number> = { linkedin: 25, indeed: 30, naukri: 40, glassdoor: 20, wellfound: 15, dice: 25, ziprecruiter: 30 };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Connected Accounts</h1>
          <p className="text-white/40 text-sm mt-1">Browser sessions are encrypted — we never see your passwords</p>
        </div>
        <div className="glass px-3 py-2 rounded-lg flex items-center gap-2 text-xs text-green-400 border border-green-500/20">
          <Shield size={13} /> AES-256 encrypted
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {PLATFORMS.map(platform => {
          const account = accounts.find(a => a.platform === platform);
          const isConnected = account?.status === "active";
          const appsToday = account?.applications_today || 0;
          const limit = DAILY_LIMITS[platform] || 20;
          const pct = Math.min(100, (appsToday / limit) * 100);
          return (
            <div key={platform} className={`glass p-5 rounded-xl border ${isConnected ? "border-green-500/20" : "border-white/08"}`}>
              <div className="flex items-center justify-between mb-3">
                <span className="font-semibold capitalize">{platform}</span>
                <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${isConnected ? "bg-green-500/15 text-green-400" : "bg-white/05 text-white/30"}`}>
                  {account?.status || "not connected"}
                </span>
              </div>
              {isConnected && (
                <div className="mb-3 space-y-1.5">
                  <div className="flex justify-between text-xs text-white/40">
                    <span>{appsToday} apps today</span>
                    <span>limit: {limit}/day</span>
                  </div>
                  <div className="h-1.5 bg-white/08 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all"
                      style={{ width: `${pct}%`, background: pct > 80 ? "#F87171" : pct > 50 ? "#FBBF24" : "#34D399" }} />
                  </div>
                  {account.last_verified && (
                    <p className="text-xs text-white/30">Verified {format(new Date(account.last_verified), "MMM d")}</p>
                  )}
                </div>
              )}
              <button className={isConnected ? "btn-ghost w-full py-2 text-sm" : "btn-primary w-full py-2 text-sm"}>
                {isConnected ? "Manage Session" : "Connect Account"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FlagsTab({ flags }: { flags: any[] }) {
  const FLAG_ICONS: Record<string, any> = {
    captcha: Shield,
    "2fa": Shield,
    suspicious_login: AlertTriangle,
    session_expired: RefreshCw,
    assignment: Briefcase,
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Human-in-the-Loop Flags</h1>
        <p className="text-white/40 text-sm mt-1">The agent paused and needs your help with these issues</p>
      </div>
      {flags.length === 0 ? (
        <div className="glass p-12 text-center rounded-xl">
          <CheckCircle2 size={40} className="text-green-400 mx-auto mb-3" />
          <p className="font-semibold text-lg">All clear!</p>
          <p className="text-white/40 text-sm mt-1">No pending flags — agent is running smoothly</p>
        </div>
      ) : (
        <div className="space-y-3">
          {flags.map(flag => {
            const Icon = FLAG_ICONS[flag.type] || AlertTriangle;
            return (
              <div key={flag.id} className="glass p-5 rounded-xl border border-amber-500/20 flex items-start gap-4">
                <div className="w-10 h-10 bg-amber-500/15 rounded-lg flex items-center justify-center shrink-0">
                  <Icon size={20} className="text-amber-400" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold capitalize">{flag.type?.replace(/_/g, " ")}</span>
                    <span className="text-xs bg-white/08 px-2 py-0.5 rounded capitalize">{flag.platform}</span>
                  </div>
                  <p className="text-sm text-white/60">{flag.description}</p>
                  <p className="text-xs text-white/30 mt-1">{flag.created_at ? format(new Date(flag.created_at), "MMM d, HH:mm") : ""}</p>
                </div>
                <button className="btn-primary px-4 py-2 text-sm shrink-0">Resolve</button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
