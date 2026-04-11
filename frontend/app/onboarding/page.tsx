"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { motion } from "framer-motion";
import { Upload, User, MapPin, DollarSign, Code, Building, ChevronRight, CheckCircle2, AlertTriangle } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

const STEPS = [
  { id: 1, title: "Upload Resume", desc: "We parse and vectorize your resume" },
  { id: 2, title: "Job Preferences", desc: "Tell us what you're looking for" },
  { id: 3, title: "Risk Agreement", desc: "Required disclosure before automation" },
  { id: 4, title: "Connect Platforms", desc: "Log into job sites once" },
];

export default function OnboardingPage() {
  const { getToken } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeParsed, setResumeParsed] = useState<any>(null);
  const [uploading, setUploading] = useState(false);
  const [prefs, setPrefs] = useState({
    job_titles: "",
    locations: "",
    salary_min: "",
    salary_max: "",
    work_type: [] as string[],
    tech_stack: "",
    daily_application_limit: 20,
    daily_email_limit: 10,
    linkedin_url: "",
  });
  const [tosAgreed, setTosAgreed] = useState(false);

  const uploadResume = async () => {
    if (!resumeFile) return;
    setUploading(true);
    try {
      const token = await getToken();
      const form = new FormData();
      form.append("file", resumeFile);
      const res = await fetch(`${API}/api/resume/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      setResumeParsed(data.parsed);
      setStep(2);
    } catch (err) {
      alert("Failed to upload resume. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const savePreferences = async () => {
    try {
      const token = await getToken();
      await fetch(`${API}/api/user/preferences`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          job_titles: prefs.job_titles.split(",").map(s => s.trim()).filter(Boolean),
          locations: prefs.locations.split(",").map(s => s.trim()).filter(Boolean),
          salary_min: prefs.salary_min ? parseInt(prefs.salary_min) : null,
          salary_max: prefs.salary_max ? parseInt(prefs.salary_max) : null,
          work_type: prefs.work_type,
          tech_stack: prefs.tech_stack.split(",").map(s => s.trim()).filter(Boolean),
          daily_application_limit: prefs.daily_application_limit,
          daily_email_limit: prefs.daily_email_limit,
          linkedin_url: prefs.linkedin_url,
          tos_agreed: false,
        }),
      });
      setStep(3);
    } catch (err) {
      alert("Failed to save preferences");
    }
  };

  const agreeToTos = async () => {
    if (!tosAgreed) return;
    try {
      const token = await getToken();
      await fetch(`${API}/api/user/preferences`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ tos_agreed: true }),
      });
      setStep(4);
    } catch (err) {
      alert("Failed to save agreement");
    }
  };

  const finish = () => router.push("/dashboard");

  return (
    <div className="min-h-screen flex">
      <div className="bg-mesh" />

      {/* Sidebar steps */}
      <aside className="relative z-10 w-80 glass border-r border-white/08 p-8 flex flex-col">
        <div className="text-xl font-bold mb-2">Get Started</div>
        <p className="text-white/40 text-sm mb-10">Setup takes about 3 minutes</p>
        <div className="space-y-4">
          {STEPS.map(s => (
            <div key={s.id} className={`flex items-start gap-3 py-3 ${s.id <= step ? "" : "opacity-40"}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${s.id < step ? "bg-green-500 text-black" : s.id === step ? "bg-indigo-500 text-white" : "bg-white/10 text-white/40"}`}>
                {s.id < step ? <CheckCircle2 size={16} /> : s.id}
              </div>
              <div>
                <p className={`font-semibold text-sm ${s.id === step ? "text-white" : "text-white/60"}`}>{s.title}</p>
                <p className="text-xs text-white/35 mt-0.5">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </aside>

      {/* Content */}
      <main className="relative z-10 flex-1 flex items-center justify-center p-10">
        <motion.div className="w-full max-w-xl" key={step} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>

          {step === 1 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-3xl font-bold mb-2">Upload Your Resume</h2>
                <p className="text-white/50">PDF or DOCX. We'll parse and store it securely.</p>
              </div>
              <div
                className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all ${resumeFile ? "border-indigo-500/50 bg-indigo-500/05" : "border-white/15 hover:border-indigo-500/40"}`}
                onClick={() => document.getElementById("resume-input")?.click()}
                onDrop={(e) => { e.preventDefault(); setResumeFile(e.dataTransfer.files[0]); }}
                onDragOver={(e) => e.preventDefault()}
              >
                <Upload size={32} className={`mx-auto mb-3 ${resumeFile ? "text-indigo-400" : "text-white/30"}`} />
                {resumeFile ? (
                  <div>
                    <p className="font-semibold text-indigo-300">{resumeFile.name}</p>
                    <p className="text-sm text-white/40">{(resumeFile.size / 1024).toFixed(0)} KB</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-white/60">Drop your resume here or <span className="text-indigo-400 underline">browse</span></p>
                    <p className="text-sm text-white/30 mt-1">PDF or DOCX, max 5MB</p>
                  </div>
                )}
                <input id="resume-input" type="file" accept=".pdf,.docx" className="hidden" onChange={(e) => setResumeFile(e.target.files?.[0] || null)} />
              </div>
              <button onClick={uploadResume} disabled={!resumeFile || uploading} className="btn-primary w-full py-4 text-base flex items-center justify-center gap-2">
                {uploading ? "Parsing with AI..." : "Continue"} <ChevronRight size={18} />
              </button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-3xl font-bold mb-2">Job Preferences</h2>
                <p className="text-white/50">The agent will only apply to matching roles</p>
              </div>
              {resumeParsed?.name && (
                <div className="glass p-4 rounded-xl flex items-center gap-3 border border-green-500/20">
                  <CheckCircle2 size={18} className="text-green-400" />
                  <p className="text-sm text-white/70">Resume parsed for <strong>{resumeParsed.name}</strong></p>
                </div>
              )}
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-white/60 mb-1.5 block">Job Titles (comma-separated)</label>
                  <input className="input-dark" placeholder="Software Engineer, Backend Developer, SDE II" value={prefs.job_titles} onChange={e => setPrefs({ ...prefs, job_titles: e.target.value })} />
                </div>
                <div>
                  <label className="text-sm font-medium text-white/60 mb-1.5 block">Locations (comma-separated)</label>
                  <input className="input-dark" placeholder="Remote, New York, London" value={prefs.locations} onChange={e => setPrefs({ ...prefs, locations: e.target.value })} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-white/60 mb-1.5 block">Min Salary ($)</label>
                    <input className="input-dark" type="number" placeholder="80000" value={prefs.salary_min} onChange={e => setPrefs({ ...prefs, salary_min: e.target.value })} />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-white/60 mb-1.5 block">Max Salary ($)</label>
                    <input className="input-dark" type="number" placeholder="150000" value={prefs.salary_max} onChange={e => setPrefs({ ...prefs, salary_max: e.target.value })} />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-white/60 mb-2 block">Work Type</label>
                  <div className="flex gap-2">
                    {["remote", "hybrid", "onsite"].map(type => (
                      <button key={type} onClick={() => setPrefs(p => ({ ...p, work_type: p.work_type.includes(type) ? p.work_type.filter(t => t !== type) : [...p.work_type, type] }))}
                        className={`px-4 py-2 text-sm rounded-lg border transition-all capitalize ${prefs.work_type.includes(type) ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-300" : "border-white/10 text-white/50 hover:border-white/20"}`}>
                        {type}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-white/60 mb-1.5 block">Daily Application Limit</label>
                  <div className="flex items-center gap-4">
                    <input type="range" min="5" max="50" value={prefs.daily_application_limit} onChange={e => setPrefs({ ...prefs, daily_application_limit: parseInt(e.target.value) })} className="flex-1 accent-indigo-500" />
                    <span className="text-indigo-300 font-bold w-8 text-center">{prefs.daily_application_limit}</span>
                  </div>
                </div>
              </div>
              <button onClick={savePreferences} className="btn-primary w-full py-4 text-base flex items-center justify-center gap-2">
                Save & Continue <ChevronRight size={18} />
              </button>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-3xl font-bold mb-2">Risk Disclosure</h2>
                <p className="text-white/50">Please read and agree before proceeding</p>
              </div>
              <div className="glass p-6 rounded-xl border border-amber-500/20 space-y-3 text-sm text-white/65 leading-relaxed max-h-64 overflow-y-auto">
                <p className="flex items-start gap-2"><AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" /> <strong className="text-white">Automated activity may violate the Terms of Service</strong> of LinkedIn, Indeed, and other job platforms. Account suspension risk is entirely borne by you, the user.</p>
                <p>• We provide residential proxies and anti-detection tools on a best-effort basis. We make no guarantee against account restrictions.</p>
                <p>• All credentials are encrypted with AES-256. Our team cannot access your passwords or session tokens.</p>
                <p>• You can disconnect any platform at any time. Session data is permanently destroyed upon disconnection or account deletion.</p>
                <p>• This platform is built for adult job seekers making informed decisions. You accept the risks willingly.</p>
                <p>• All outreach emails are opt-in only and comply with GDPR and CAN-SPAM.</p>
              </div>
              <label className="flex items-start gap-3 cursor-pointer">
                <input type="checkbox" checked={tosAgreed} onChange={e => setTosAgreed(e.target.checked)} className="mt-1 w-4 h-4 accent-indigo-500" />
                <span className="text-sm text-white/70">I understand the risks and agree to the <span className="text-indigo-400 underline">Terms of Service</span>. I accept full responsibility for any account actions.</span>
              </label>
              <button onClick={agreeToTos} disabled={!tosAgreed} className="btn-primary w-full py-4 text-base flex items-center justify-center gap-2 disabled:opacity-40">
                I Agree — Continue <ChevronRight size={18} />
              </button>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-3xl font-bold mb-2">Connect Your Accounts</h2>
                <p className="text-white/50">Log in once. Your session is encrypted and reused.</p>
              </div>
              <div className="space-y-3">
                {["linkedin", "indeed", "glassdoor"].map(platform => (
                  <div key={platform} className="glass p-4 rounded-xl flex items-center justify-between">
                    <span className="font-semibold capitalize">{platform}</span>
                    <button className="btn-primary text-sm px-5 py-2">Connect</button>
                  </div>
                ))}
              </div>
              <button onClick={finish} className="btn-primary w-full py-4 text-base flex items-center justify-center gap-2">
                Go to Dashboard <ChevronRight size={18} />
              </button>
            </div>
          )}

        </motion.div>
      </main>
    </div>
  );
}
