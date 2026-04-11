"use client";
import { useState } from "react";
import Link from "next/link";
import {
  Clock, Send, CheckCircle2, Download, Bell, Globe, AlertTriangle,
  User, CreditCard, ArrowRight, Shield, BarChart3
} from "lucide-react";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, PieChart, Pie, Cell } from "recharts";
import { format } from "date-fns";

// ─── Outreach Tab ─────────────────────────────────────────────────────────────
export function OutreachTab({ contacts, emails }: { contacts: any[]; emails: any[] }) {
  const EMAIL_STATUS_STYLES: Record<string, string> = {
    draft:   "bg-white/08 text-white/40",
    pending: "bg-amber-500/15 text-amber-400",
    sent:    "bg-indigo-500/15 text-indigo-400",
    opened:  "bg-blue-500/15 text-blue-400",
    replied: "bg-green-500/15 text-green-400",
    bounced: "bg-red-500/15 text-red-400",
  };
  const SEQUENCE_LABELS: Record<string, string> = {
    initial: "Initial cold email",
    day3:    "Day 3 follow-up",
    day7:    "Day 7 follow-up",
    day14:   "Day 14 follow-up",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Cold Outreach</h1>
          <p className="text-white/40 text-sm mt-1">Human-reviewed emails sent to hiring managers on your behalf</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-white/40">
          <Clock size={13} /> Sequences: Day 0 → 3 → 7 → 14
        </div>
      </div>

      {/* Email sequences table */}
      <div className="glass rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-white/08 flex items-center justify-between">
          <h2 className="font-semibold">Email Sequences</h2>
          <span className="text-xs text-white/30">{emails.length} emails</span>
        </div>
        {emails.length === 0 ? (
          <div className="py-16 text-center text-white/30 text-sm">
            <Send size={36} className="mx-auto mb-3 opacity-20" />
            <p>No outreach emails yet.</p>
            <p className="mt-1 text-xs">Start the agent and enable cold email to generate sequences.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/08">
                {["Contact", "Company", "Type", "Subject", "Status", "Sent", "Action"].map(h => (
                  <th key={h} className="text-left py-3 px-4 text-xs font-semibold text-white/40 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {emails.map((email: any) => {
                const contact = contacts.find((c: any) => c.id === email.contact_id);
                return (
                  <tr key={email.id} className="border-b border-white/05 hover:bg-white/02 transition-colors">
                    <td className="py-3 px-4 text-sm font-medium">{contact?.name || "—"}</td>
                    <td className="py-3 px-4 text-sm text-white/60">{contact?.company || "—"}</td>
                    <td className="py-3 px-4 text-xs text-white/40">{SEQUENCE_LABELS[email.type] || email.type}</td>
                    <td className="py-3 px-4 text-sm text-white/70 max-w-[200px] truncate">{email.subject}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${EMAIL_STATUS_STYLES[email.status] || EMAIL_STATUS_STYLES.draft}`}>
                        {email.status}{email.opened && " · opened"}{email.replied && " · replied"}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-xs text-white/35">
                      {email.sent_at ? format(new Date(email.sent_at), "MMM d, HH:mm") : "—"}
                    </td>
                    <td className="py-3 px-4">
                      {!email.approved && (
                        <button className="btn-primary text-xs px-3 py-1.5">Approve & Send</button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Contacts */}
      <div>
        <h2 className="font-semibold mb-3">Identified Contacts ({contacts.length})</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {contacts.length === 0 ? (
            <div className="col-span-3 glass p-8 rounded-xl text-center text-white/30 text-sm">
              No contacts yet. Run the agent with cold email enabled.
            </div>
          ) : contacts.map((c: any) => (
            <div key={c.id} className="glass p-4 rounded-xl">
              <p className="font-medium text-sm">{c.name}</p>
              <p className="text-xs text-white/50">{c.title} · {c.company}</p>
              {c.email && <p className="text-xs text-indigo-400 mt-1">{c.email}</p>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Analytics Tab ────────────────────────────────────────────────────────────
export function AnalyticsTab({ stats, chartData, weeklyData, colors, applications }: any) {
  const platformCounts: Record<string, number> = {};
  (applications || []).forEach((a: any) => {
    if (a.platform) platformCounts[a.platform] = (platformCounts[a.platform] || 0) + 1;
  });
  const platformData = Object.entries(platformCounts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  const STAT_CARDS = [
    { label: "Total Applied",   value: stats?.applications?.total ?? 0,                  color: "text-indigo-400" },
    { label: "Interviews",      value: stats?.applications?.by_status?.interview ?? 0,   color: "text-green-400"  },
    { label: "Offers",          value: stats?.applications?.by_status?.offer ?? 0,       color: "text-amber-400"  },
    { label: "Response Rate",   value: `${stats?.applications?.interview_rate ?? 0}%`,   color: "text-blue-400"   },
    { label: "Emails Sent",     value: stats?.outreach?.total_sent ?? 0,                 color: "text-violet-400" },
    { label: "Email Replies",   value: stats?.outreach?.replies ?? 0,                    color: "text-pink-400"   },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Analytics</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {STAT_CARDS.map(s => (
          <div key={s.label} className="glass p-5 rounded-xl">
            <div className={`text-3xl font-black mb-1 ${s.color}`}>{s.value}</div>
            <div className="text-sm text-white/45">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Weekly trend */}
        <div className="glass p-6 rounded-xl">
          <h3 className="font-semibold mb-5">Weekly Applications</h3>
          {weeklyData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={weeklyData}>
                <XAxis dataKey="day" tick={{ fill: "rgba(255,255,255,0.35)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "rgba(255,255,255,0.35)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "#0D1220", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
                <Area type="monotone" dataKey="count" stroke="#818CF8" fill="rgba(99,102,241,0.15)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-white/30 text-sm">No data yet — start the agent!</div>
          )}
        </div>

        {/* Platform breakdown */}
        <div className="glass p-6 rounded-xl">
          <h3 className="font-semibold mb-5">By Platform</h3>
          {platformData.length > 0 ? (
            <div className="space-y-3">
              {platformData.map((p, i) => {
                const max = platformData[0].value;
                return (
                  <div key={p.name} className="flex items-center gap-3">
                    <span className="text-sm text-white/60 capitalize w-24 shrink-0">{p.name}</span>
                    <div className="flex-1 h-2 bg-white/08 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${(p.value / max) * 100}%`, background: colors[i % colors.length] }} />
                    </div>
                    <span className="text-sm text-white/60 w-8 text-right">{p.value}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-white/30 text-sm">No applications yet</div>
          )}
        </div>
      </div>

      {/* Funnel */}
      {chartData.length > 0 && (
        <div className="glass p-6 rounded-xl">
          <h3 className="font-semibold mb-5">Status Funnel</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={chartData} cx="50%" cy="50%" outerRadius={80} dataKey="value"
                label={({ name, value }) => `${name}: ${value}`}>
                {chartData.map((_: any, i: number) => <Cell key={i} fill={colors[i % colors.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: "#0D1220", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ─── Settings Tab ─────────────────────────────────────────────────────────────
export function SettingsTab({ user }: { user: any }) {
  const [notifs, setNotifs] = useState({
    agentPause: true, captchaFlag: true, newInterview: true, weeklyDigest: true,
  });
  const [deleteConfirm, setDeleteConfirm] = useState("");

  return (
    <div className="space-y-8 max-w-2xl">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Profile */}
      <div className="glass p-6 rounded-xl space-y-4">
        <h2 className="font-semibold flex items-center gap-2">
          <User size={16} className="text-indigo-400" /> Profile
        </h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-white/40 mb-1">Name</p>
            <p className="font-medium">{user?.fullName || "—"}</p>
          </div>
          <div>
            <p className="text-white/40 mb-1">Email</p>
            <p className="font-medium">{user?.primaryEmailAddress?.emailAddress || "—"}</p>
          </div>
        </div>
        <p className="text-xs text-white/30">To update your name or email, use the avatar menu in the sidebar footer.</p>
      </div>

      {/* Plan */}
      <div className="glass p-6 rounded-xl space-y-4">
        <h2 className="font-semibold flex items-center gap-2">
          <CreditCard size={16} className="text-indigo-400" /> Plan & Billing
        </h2>
        <div className="flex items-center justify-between p-4 rounded-xl bg-white/04 border border-white/08">
          <div>
            <p className="font-semibold text-sm">Free Plan</p>
            <p className="text-xs text-white/40 mt-0.5">20 applications · 5 cold emails · 1 platform</p>
          </div>
          <Link href="/pricing">
            <button className="btn-primary text-sm px-5 py-2 flex items-center gap-2">
              Upgrade to Pro <ArrowRight size={14} />
            </button>
          </Link>
        </div>
      </div>

      {/* Notifications */}
      <div className="glass p-6 rounded-xl space-y-5">
        <h2 className="font-semibold flex items-center gap-2">
          <Bell size={16} className="text-indigo-400" /> Notification Preferences
        </h2>
        {[
          { key: "agentPause",   label: "Agent paused (requires attention)" },
          { key: "captchaFlag",  label: "CAPTCHA / 2FA flag detected" },
          { key: "newInterview", label: "New interview invitation received" },
          { key: "weeklyDigest", label: "Weekly activity digest" },
        ].map(({ key, label }) => (
          <div key={key} className="flex items-center justify-between">
            <span className="text-sm text-white/70">{label}</span>
            <button
              onClick={() => setNotifs(n => ({ ...n, [key]: !n[key as keyof typeof n] }))}
              className={`relative w-10 h-5 rounded-full transition-colors shrink-0 ${(notifs as any)[key] ? "bg-indigo-500" : "bg-white/15"}`}>
              <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${(notifs as any)[key] ? "left-5" : "left-0.5"}`} />
            </button>
          </div>
        ))}
      </div>

      {/* GDPR */}
      <div className="glass p-6 rounded-xl space-y-4">
        <h2 className="font-semibold flex items-center gap-2">
          <Globe size={16} className="text-indigo-400" /> Data & Privacy (GDPR)
        </h2>
        <p className="text-white/50 text-sm">Download a full copy of your data or request permanent deletion.</p>
        <button className="btn-ghost text-sm px-5 py-2.5 flex items-center gap-2">
          <Download size={14} /> Export My Data
        </button>
        <p className="text-xs text-white/30">Delivered to your email within 48 hours per GDPR Article 20.</p>
      </div>

      {/* Danger zone */}
      <div className="glass p-6 rounded-xl space-y-4 border border-red-500/20">
        <h2 className="font-semibold text-red-400 flex items-center gap-2">
          <AlertTriangle size={16} /> Danger Zone
        </h2>
        <p className="text-white/50 text-sm">
          Permanently destroys all applications, emails, platform sessions, and resume data.
          <strong className="text-white"> Cannot be undone.</strong>
        </p>
        <div className="space-y-3">
          <input
            type="text"
            placeholder={`Type "delete" to confirm`}
            value={deleteConfirm}
            onChange={e => setDeleteConfirm(e.target.value)}
            className="input-dark text-sm"
          />
          <button
            disabled={deleteConfirm !== "delete"}
            className="px-5 py-2.5 text-sm font-semibold rounded-lg border border-red-500/40 text-red-400 bg-red-500/10 hover:bg-red-500/20 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            onClick={() => alert("Account deletion request submitted. You'll receive a confirmation email within 24 hours.")}>
            Delete My Account & All Data
          </button>
        </div>
      </div>
    </div>
  );
}
