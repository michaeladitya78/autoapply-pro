'use client';
import Link from 'next/link';
import {
  Bot, Briefcase, Mail, Shield, LayoutDashboard, BarChart3,
  TrendingUp, Zap, CheckCircle2, Clock, Play, ArrowRight,
  AlertTriangle, RefreshCw
} from 'lucide-react';
import { motion } from 'framer-motion';

// ─── Fake Data ────────────────────────────────────────────────────────────────
const FAKE_STATS = {
  totalApplications: 312,
  thisWeek: 47,
  interviewRate: '8.3',
  emailResponseRate: '14.6',
};

const FAKE_APPLICATIONS = [
  { id: 1, company: 'Stripe', title: 'Senior Software Engineer', platform: 'LinkedIn', status: 'interview', appliedAt: 'Apr 9, 14:22' },
  { id: 2, company: 'Notion', title: 'Full-Stack Engineer', platform: 'Indeed', status: 'viewed', appliedAt: 'Apr 9, 11:05' },
  { id: 3, company: 'Vercel', title: 'Frontend Engineer', platform: 'Wellfound', status: 'applied', appliedAt: 'Apr 8, 18:41' },
  { id: 4, company: 'Linear', title: 'Product Engineer', platform: 'LinkedIn', status: 'applied', appliedAt: 'Apr 8, 15:30' },
  { id: 5, company: 'Figma', title: 'Software Engineer II', platform: 'Glassdoor', status: 'rejected', appliedAt: 'Apr 7, 09:15' },
];

const FAKE_ACTIVITY = [
  { id: 1, type: 'Application submitted', company: 'Stripe', platform: 'LinkedIn', time: '14:22:08', dot: 'indigo' },
  { id: 2, type: 'Cold email sent', company: 'Notion', platform: 'Gmail', time: '13:55:31', dot: 'blue' },
  { id: 3, type: 'Application submitted', company: 'Vercel', platform: 'Wellfound', time: '13:21:44', dot: 'indigo' },
  { id: 4, type: 'Follow-up email sent', company: 'Linear', platform: 'Gmail', time: '12:47:19', dot: 'blue' },
  { id: 5, type: 'Profile viewed by recruiter', company: 'Figma', platform: 'LinkedIn', time: '11:03:55', dot: 'emerald' },
];

const FAKE_ACCOUNTS = [
  { platform: 'LinkedIn', status: 'active', appsToday: 23, verified: 'Apr 10' },
  { platform: 'Indeed', status: 'active', appsToday: 18, verified: 'Apr 10' },
  { platform: 'Glassdoor', status: 'not connected', appsToday: 0, verified: null },
  { platform: 'Wellfound', status: 'not connected', appsToday: 0, verified: null },
];

const STATUS_STYLES: Record<string, string> = {
  interview: 'badge-interview',
  viewed:    'badge-viewed',
  applied:   'badge-applied',
  rejected:  'badge-rejected',
  offer:     'badge-offer',
};

const STATUS_LABELS: Record<string, string> = {
  interview: 'Interview',
  viewed:    'Viewed',
  applied:   'Applied',
  rejected:  'Rejected',
  offer:     'Offer!',
};

// ─── Component ────────────────────────────────────────────────────────────────
export default function DemoPage() {
  const metrics = [
    { label: 'Total Applications', value: FAKE_STATS.totalApplications, icon: Briefcase, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
    { label: 'This Week',          value: FAKE_STATS.thisWeek,          icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { label: 'Interview Rate',     value: `${FAKE_STATS.interviewRate}%`, icon: Zap,  color: 'text-amber-400', bg: 'bg-amber-500/10' },
    { label: 'Email Response Rate', value: `${FAKE_STATS.emailResponseRate}%`, icon: Mail, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      <div className="bg-mesh" />

      {/* ── Demo Banner ─────────────────────────────────────────────────────── */}
      <div className="relative z-20 bg-indigo-600/90 backdrop-blur-sm text-white text-center py-2.5 px-4 text-sm font-medium flex items-center justify-center gap-3">
        <span>👋 This is a read-only demo — data is illustrative only</span>
        <Link href="/sign-up">
          <button className="bg-white text-indigo-700 px-4 py-1 rounded-full text-xs font-bold hover:bg-indigo-50 transition-colors">
            Start for free →
          </button>
        </Link>
      </div>

      <div className="flex flex-1 relative z-10">
        {/* ── Sidebar ───────────────────────────────────────────────────────── */}
        <aside className="w-64 shrink-0 glass border-r border-white/08 rounded-none flex flex-col py-6 px-4">
          <div className="flex items-center gap-2 px-2 mb-8">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <Bot size={18} className="text-white" />
            </div>
            <span className="font-bold tracking-tight">AutoApply Pro</span>
          </div>

          {/* Agent status card */}
          <div className="glass p-4 mb-6 rounded-xl border border-green-500/30 glow-green">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium">Agent Status</span>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-green-400">
                <span className="w-2 h-2 rounded-full bg-green-400 pulse-dot" />
                LIVE
              </div>
            </div>
            <button className="w-full flex items-center justify-center gap-2 py-2.5 text-sm font-semibold rounded-lg bg-orange-500/20 text-orange-400 border border-orange-500/30">
              <Play size={15} />
              Agent Running (Demo)
            </button>
          </div>

          <nav className="flex-1 space-y-1">
            {[
              { icon: LayoutDashboard, label: 'Overview',     active: true },
              { icon: Briefcase,       label: 'Applications', active: false },
              { icon: Mail,            label: 'Outreach',     active: false },
              { icon: Shield,          label: 'Accounts',     active: false },
              { icon: AlertTriangle,   label: 'Flags',        active: false },
              { icon: BarChart3,       label: 'Analytics',    active: false },
            ].map(item => (
              <div key={item.label}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium ${
                  item.active
                    ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/20'
                    : 'text-white/50'
                }`}>
                <item.icon size={17} />
                {item.label}
              </div>
            ))}
          </nav>

          <div className="border-t border-white/08 pt-4 px-2">
            <Link href="/sign-up">
              <button className="btn-primary w-full py-2.5 text-sm flex items-center justify-center gap-2">
                Start for free <ArrowRight size={15} />
              </button>
            </Link>
          </div>
        </aside>

        {/* ── Main Content ──────────────────────────────────────────────────── */}
        <main className="flex-1 overflow-auto p-8 space-y-8">

          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Overview</h1>
              <p className="text-white/40 text-sm mt-1">Your agent&apos;s performance at a glance (demo data)</p>
            </div>
            <div className="flex items-center gap-2 text-sm text-white/40">
              <RefreshCw size={14} />
              Updates every 15s
            </div>
          </div>

          {/* ── Stats Cards ───────────────────────────────────────────────── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {metrics.map((m, i) => (
              <motion.div key={m.label} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }} className="glass p-5 rounded-xl">
                <div className={`w-10 h-10 ${m.bg} rounded-lg flex items-center justify-center mb-4`}>
                  <m.icon size={20} className={m.color} />
                </div>
                <div className="text-3xl font-black mb-1">{m.value}</div>
                <div className="text-sm text-white/45">{m.label}</div>
              </motion.div>
            ))}
          </div>

          {/* ── Application Tracker Table ─────────────────────────────────── */}
          <div>
            <h2 className="text-lg font-semibold mb-4">Recent Applications</h2>
            <div className="glass rounded-xl overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/08">
                    {['Company', 'Role', 'Platform', 'Status', 'Applied'].map(h => (
                      <th key={h} className="text-left py-3 px-4 text-xs font-semibold text-white/40 uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {FAKE_APPLICATIONS.map(app => (
                    <tr key={app.id} className="border-b border-white/05 hover:bg-white/02 transition-colors">
                      <td className="py-3 px-4 font-medium text-sm">{app.company}</td>
                      <td className="py-3 px-4 text-sm text-white/70">{app.title}</td>
                      <td className="py-3 px-4 text-sm text-white/50">{app.platform}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${STATUS_STYLES[app.status] || 'badge-applied'}`}>
                          {STATUS_LABELS[app.status] || app.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-xs text-white/40">{app.appliedAt}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* ── Activity Log + Connected Accounts ─────────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Activity Log */}
            <div className="glass p-6 rounded-xl">
              <h3 className="font-semibold mb-4">Live Agent Activity</h3>
              <div className="space-y-3">
                {FAKE_ACTIVITY.map(action => (
                  <div key={action.id} className="flex items-start gap-3 py-2 border-b border-white/05 last:border-0">
                    <div className={`w-2 h-2 mt-2 rounded-full shrink-0 ${
                      action.dot === 'indigo' ? 'bg-indigo-400' :
                      action.dot === 'blue'   ? 'bg-blue-400' : 'bg-emerald-400'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white/80">
                        {action.type} — {action.company}
                      </p>
                      <p className="text-xs text-white/35 mt-0.5">
                        {action.platform} · {action.time}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Connected Accounts */}
            <div className="glass p-6 rounded-xl">
              <h3 className="font-semibold mb-4">Connected Accounts</h3>
              <div className="space-y-3">
                {FAKE_ACCOUNTS.map(acc => {
                  const isConnected = acc.status === 'active';
                  return (
                    <div key={acc.platform}
                      className={`flex items-center justify-between p-3 rounded-xl border ${
                        isConnected ? 'border-green-500/20 bg-green-500/05' : 'border-white/08'
                      }`}>
                      <div>
                        <p className="font-semibold text-sm">{acc.platform}</p>
                        {isConnected && (
                          <p className="text-xs text-white/40">{acc.appsToday} apps today · Verified {acc.verified}</p>
                        )}
                      </div>
                      <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                        isConnected
                          ? 'bg-green-500/15 text-green-400'
                          : 'bg-white/05 text-white/30'
                      }`}>
                        {isConnected ? 'Connected' : 'Not connected'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* ── CTA Banner ────────────────────────────────────────────────── */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="glass p-8 rounded-2xl border border-indigo-500/30 glow-indigo text-center">
            <h2 className="text-2xl font-bold mb-2">Ready to automate your job search?</h2>
            <p className="text-white/50 mb-6">Start your free account and have the agent running in under 5 minutes.</p>
            <Link href="/sign-up">
              <button className="btn-primary px-8 py-4 text-base inline-flex items-center gap-2 glow-indigo">
                Start for free — No credit card <ArrowRight size={18} />
              </button>
            </Link>
          </motion.div>
        </main>
      </div>
    </div>
  );
}
