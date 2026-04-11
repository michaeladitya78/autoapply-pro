"use client";
import { useState, useEffect, useCallback } from "react";
import {
  Bot, RefreshCw, Search, Target, FileText, GitBranch,
  Send, Star, PlusCircle, Clock, CheckCircle2, XCircle, BarChart3,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

interface CareerOpsTabProps {
  getToken: () => Promise<string | null>;
  userId: string;
}

async function authFetch(getToken: () => Promise<string | null>, endpoint: string, opts?: RequestInit) {
  const token = await getToken();
  const res = await fetch(`${API}${endpoint}`, {
    ...opts,
    headers: { Authorization: `Bearer ${token}`, ...(opts?.headers || {}) },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export default function CareerOpsTab({ getToken, userId }: CareerOpsTabProps) {
  const [activeSection, setActiveSection] = useState<"pipeline" | "patterns" | "followups">("pipeline");
  const [pipeline, setPipeline] = useState<string[]>([]);
  const [urlInput, setUrlInput] = useState("");
  const [noteInput, setNoteInput] = useState("");
  const [patterns, setPatterns] = useState<any>(null);
  const [followups, setFollowups] = useState<any>(null);
  const [scanning, setScanning] = useState(false);
  const [addingUrl, setAddingUrl] = useState(false);
  const [loadingPatterns, setLoadingPatterns] = useState(false);
  const [loadingFollowups, setLoadingFollowups] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);

  const showToast = (msg: string, type: "success" | "error" = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const post = (endpoint: string, body?: any) =>
    authFetch(getToken, endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });

  const loadPipeline = useCallback(async () => {
    try {
      const data = await authFetch(getToken, "/api/career-ops/pipeline");
      setPipeline(data.urls || []);
    } catch { /* silent */ }
  }, [getToken]);

  useEffect(() => { loadPipeline(); }, [loadPipeline]);

  const handleAddUrl = async () => {
    if (!urlInput.trim()) return;
    setAddingUrl(true);
    try {
      await post("/api/career-ops/pipeline", { url: urlInput.trim(), note: noteInput.trim() });
      setUrlInput(""); setNoteInput("");
      await loadPipeline();
      showToast("Job URL added to pipeline ✓");
    } catch { showToast("Failed to add URL", "error"); }
    finally { setAddingUrl(false); }
  };

  const handleScan = async () => {
    setScanning(true);
    try {
      await post("/api/career-ops/scan");
      showToast("Portal scan queued — check pipeline in a few minutes");
      setTimeout(loadPipeline, 6000);
    } catch { showToast("Failed to start scan", "error"); }
    finally { setScanning(false); }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const data = await post("/api/career-ops/sync");
      showToast(`Synced ${data.rows_upserted} rows from career-ops tracker`);
    } catch { showToast("Sync failed", "error"); }
    finally { setSyncing(false); }
  };

  const loadPatterns = async () => {
    setLoadingPatterns(true);
    try { setPatterns(await authFetch(getToken, "/api/career-ops/patterns")); }
    catch { showToast("Pattern analysis failed", "error"); }
    finally { setLoadingPatterns(false); }
  };

  const loadFollowups = async () => {
    setLoadingFollowups(true);
    try { setFollowups(await authFetch(getToken, "/api/career-ops/followups")); }
    catch { showToast("Follow-up load failed", "error"); }
    finally { setLoadingFollowups(false); }
  };

  const SECTIONS = [
    { id: "pipeline", label: "Pipeline", icon: GitBranch },
    { id: "patterns", label: "Patterns", icon: BarChart3 },
    { id: "followups", label: "Follow-Ups", icon: Send },
  ] as const;

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-6 right-6 z-50 px-5 py-3 rounded-xl text-sm font-medium shadow-lg flex items-center gap-2 ${toast.type === "success" ? "bg-emerald-500/20 border border-emerald-500/30 text-emerald-300" : "bg-red-500/20 border border-red-500/30 text-red-300"}`}>
          {toast.type === "success" ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <span className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
              <Target size={18} className="text-white" />
            </span>
            Career-Ops
          </h1>
          <p className="text-white/40 text-sm mt-1">AI-powered job search pipeline · Evaluate → Score → Apply</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleSync} disabled={syncing} className="btn-ghost px-4 py-2 text-sm flex items-center gap-2">
            <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
            {syncing ? "Syncing..." : "Sync Tracker"}
          </button>
          <button onClick={handleScan} disabled={scanning} className="btn-primary px-4 py-2 text-sm flex items-center gap-2">
            <Search size={14} className={scanning ? "animate-spin" : ""} />
            {scanning ? "Scanning..." : "Scan Portals"}
          </button>
        </div>
      </div>

      {/* Integration notice */}
      <div className="glass p-4 rounded-xl border border-violet-500/20 flex items-start gap-3">
        <div className="w-8 h-8 bg-violet-500/15 rounded-lg flex items-center justify-center shrink-0">
          <Bot size={16} className="text-violet-400" />
        </div>
        <div>
          <p className="text-sm font-medium text-violet-300">Claude Code Integration</p>
          <p className="text-xs text-white/45 mt-0.5">
            Add URLs here, then open Claude Code in your{" "}
            <code className="px-1 py-0.5 rounded bg-white/08 text-white/70 font-mono">career-ops/</code> folder and run{" "}
            <code className="px-1 py-0.5 rounded bg-white/08 text-white/70 font-mono">/career-ops pipeline</code>.
            AI scores each job A–F, generates a tailored PDF, and results sync back every 15 min.
          </p>
        </div>
      </div>

      {/* Section tabs */}
      <div className="flex gap-2">
        {SECTIONS.map(s => (
          <button key={s.id} onClick={() => setActiveSection(s.id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm rounded-lg border transition-all ${activeSection === s.id ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-300" : "border-white/10 text-white/50 hover:border-white/20"}`}>
            <s.icon size={14} />{s.label}
          </button>
        ))}
      </div>

      {/* Pipeline */}
      {activeSection === "pipeline" && (
        <div className="space-y-4">
          <div className="glass p-5 rounded-xl">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <PlusCircle size={16} className="text-indigo-400" /> Add Job URL
            </h3>
            <div className="flex flex-col gap-3">
              <input
                id="career-ops-url"
                type="url"
                placeholder="https://linkedin.com/jobs/view/... or any job posting URL"
                value={urlInput}
                onChange={e => setUrlInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleAddUrl()}
                className="w-full px-4 py-2.5 rounded-lg bg-white/05 border border-white/10 text-sm text-white placeholder-white/30 focus:outline-none focus:border-indigo-500/50"
              />
              <div className="flex gap-3">
                <input type="text" placeholder="Optional note (e.g. 'referral from Jane')"
                  value={noteInput} onChange={e => setNoteInput(e.target.value)}
                  className="flex-1 px-4 py-2.5 rounded-lg bg-white/05 border border-white/10 text-sm text-white placeholder-white/30 focus:outline-none focus:border-indigo-500/50" />
                <button onClick={handleAddUrl} disabled={addingUrl || !urlInput.trim()} className="btn-primary px-5 py-2 text-sm flex items-center gap-2 shrink-0">
                  <PlusCircle size={14} />{addingUrl ? "Adding..." : "Add"}
                </button>
              </div>
            </div>
          </div>

          <div className="glass rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/08">
              <h3 className="font-semibold flex items-center gap-2">
                <Clock size={15} className="text-white/40" /> Pending Jobs
                <span className="px-2 py-0.5 text-xs bg-white/08 rounded-full">{pipeline.length}</span>
              </h3>
              <button onClick={loadPipeline} className="text-white/30 hover:text-white/60 transition-colors"><RefreshCw size={14} /></button>
            </div>
            {pipeline.length === 0 ? (
              <div className="py-12 text-center text-white/30 text-sm">
                <GitBranch size={32} className="mx-auto mb-3 opacity-20" />
                No pending URLs. Add one above or run a portal scan.
              </div>
            ) : (
              <div className="divide-y divide-white/05">
                {pipeline.map((url, i) => (
                  <div key={i} className="flex items-center gap-4 px-5 py-3 hover:bg-white/02 transition-colors">
                    <div className="w-6 h-6 rounded-md bg-indigo-500/15 flex items-center justify-center shrink-0">
                      <FileText size={12} className="text-indigo-400" />
                    </div>
                    <a href={url} target="_blank" rel="noopener noreferrer" className="flex-1 text-sm text-white/70 hover:text-white truncate">{url}</a>
                    <span className="text-xs text-white/25 shrink-0">Pending</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="glass p-5 rounded-xl border border-white/05">
            <h4 className="text-sm font-semibold mb-3 text-white/70">How it works</h4>
            <ol className="space-y-2 text-sm text-white/50">
              {["Add job URLs above (or click 'Scan Portals' to auto-discover)",
                "Open Claude Code in your career-ops/ directory",
                "Run /career-ops pipeline — AI scores each job A–F and generates a tailored CV",
                "Hit 'Sync Tracker' to pull results back into this dashboard"].map((step, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 text-xs flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                    {step}
                  </li>
              ))}
            </ol>
          </div>
        </div>
      )}

      {/* Patterns */}
      {activeSection === "patterns" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">Rejection Pattern Analysis</h3>
              <p className="text-white/40 text-xs mt-0.5">Discover why you&apos;re being passed over and how to fix it</p>
            </div>
            <button onClick={loadPatterns} disabled={loadingPatterns} className="btn-primary px-4 py-2 text-sm flex items-center gap-2">
              <BarChart3 size={14} className={loadingPatterns ? "animate-spin" : ""} />
              {loadingPatterns ? "Analyzing..." : "Run Analysis"}
            </button>
          </div>
          {!patterns ? (
            <div className="glass p-12 text-center rounded-xl text-white/30 text-sm">
              <BarChart3 size={36} className="mx-auto mb-3 opacity-20" />
              Click &quot;Run Analysis&quot; to detect patterns in your applications
            </div>
          ) : (
            <div className="glass p-6 rounded-xl space-y-4">
              {patterns.summary && <div className="p-4 rounded-lg bg-white/04 border border-white/08"><p className="text-sm text-white/70">{patterns.summary}</p></div>}
              {(patterns.patterns || []).map((p: any, i: number) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-white/03">
                  <Star size={15} className="text-amber-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium">{p.pattern || p.title}</p>
                    {p.recommendation && <p className="text-xs text-white/45 mt-1">{p.recommendation}</p>}
                  </div>
                </div>
              ))}
              {!patterns.patterns?.length && <p className="text-white/40 text-sm text-center py-4">No patterns detected yet — apply to more roles first</p>}
            </div>
          )}
        </div>
      )}

      {/* Follow-ups */}
      {activeSection === "followups" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">Follow-Up Cadence</h3>
              <p className="text-white/40 text-xs mt-0.5">Smart reminders based on application age and status</p>
            </div>
            <button onClick={loadFollowups} disabled={loadingFollowups} className="btn-primary px-4 py-2 text-sm flex items-center gap-2">
              <Send size={14} className={loadingFollowups ? "animate-spin" : ""} />
              {loadingFollowups ? "Loading..." : "Check Follow-Ups"}
            </button>
          </div>
          {!followups ? (
            <div className="glass p-12 text-center rounded-xl text-white/30 text-sm">
              <Send size={36} className="mx-auto mb-3 opacity-20" />
              Click &quot;Check Follow-Ups&quot; to see which applications need action today
            </div>
          ) : (
            <div className="space-y-3">
              {followups.due?.length === 0 && (
                <div className="glass p-8 text-center rounded-xl">
                  <CheckCircle2 size={36} className="text-emerald-400 mx-auto mb-3" />
                  <p className="font-semibold">All caught up!</p>
                  <p className="text-white/40 text-sm mt-1">No follow-ups due today.</p>
                </div>
              )}
              {(followups.due || []).map((item: any, i: number) => (
                <div key={i} className="glass p-4 rounded-xl flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">{item.company} — {item.role}</p>
                    <p className="text-xs text-white/45 mt-0.5">{item.days_since} days since last contact · {item.action}</p>
                  </div>
                  <span className={`px-2.5 py-1 text-xs rounded-full font-medium ${item.priority === "high" ? "bg-red-500/15 text-red-400" : item.priority === "medium" ? "bg-amber-500/15 text-amber-400" : "bg-white/08 text-white/50"}`}>
                    {item.priority || "normal"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
