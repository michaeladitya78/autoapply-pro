"use client";
import Link from "next/link";
import { SignInButton, SignUpButton, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { Bot, Zap, Shield, LineChart, ArrowRight, CheckCircle2, Eye } from "lucide-react";

const FEATURES = [
  { icon: Bot, title: "Fully Autonomous Agent", desc: "AI applies to hundreds of jobs daily — LinkedIn, Indeed, Glassdoor, and 10+ more platforms — without you lifting a finger." },
  { icon: Zap, title: "Cold Email Outreach", desc: "Claude drafts hyper-personalized outreach to hiring managers. Day 3, 7, 14 follow-ups sent automatically." },
  { icon: Shield, title: "Stealth Anti-Detection", desc: "Residential proxies, human-speed behavior, browser fingerprint normalization. Your accounts stay safe." },
  { icon: LineChart, title: "Real-Time Dashboard", desc: "Track every application, email, and interview invitation live. Full transparency on agent actions." },
];

const STATS = [
  { value: "847", label: "Avg Applications/Month" },
  { value: "4.2x", label: "Interview Rate vs Manual" },
  { value: "6hrs", label: "Saved Per Day" },
  { value: "99.7%", label: "Uptime" },
];

export default function LandingPage() {
  const { isSignedIn } = useUser();
  const router = useRouter();

  useEffect(() => {
    if (isSignedIn) router.push("/dashboard");
  }, [isSignedIn, router]);

  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="bg-mesh" />

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-6 py-5 max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
            <Bot size={18} className="text-white" />
          </div>
          <span className="font-bold text-lg tracking-tight">AutoApply Pro</span>
        </div>
        <div className="flex items-center gap-3">
          <SignInButton mode="modal">
            <button className="btn-ghost py-2 px-5 text-sm">Sign In</button>
          </SignInButton>
          <SignUpButton mode="modal">
            <button className="btn-primary py-2 px-5 text-sm">Get Started Free</button>
          </SignUpButton>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 pt-20 pb-24 text-center">
        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}>
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-sm text-indigo-300 font-medium mb-8">
            <span className="w-2 h-2 rounded-full bg-green-400 pulse-dot" />
            Now in Beta — Free tier available
          </div>

          <h1 className="text-6xl md:text-7xl font-black leading-[1.05] tracking-tight mb-6">
            Your AI Applies to <br />
            <span className="gradient-text">1,000 Jobs for You</span>
          </h1>

          <p className="text-xl text-white/60 max-w-2xl mx-auto mb-10 leading-relaxed">
            An autonomous AI agent that scrapes listings, tailors your resume per job, fills every form, 
            sends cold emails, follows up — and schedules your interviews. <strong className="text-white/80">Zero clicks required.</strong>
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <SignUpButton mode="modal">
              <button className="btn-primary px-8 py-4 text-base flex items-center gap-2 glow-indigo">
                Start Free — No Credit Card <ArrowRight size={18} />
              </button>
            </SignUpButton>
            <Link href="/demo">
              <button className="btn-ghost px-8 py-4 text-base flex items-center gap-2">
                <Eye size={18} />
                See the dashboard →
              </button>
            </Link>
          </div>

          <div className="flex justify-center gap-8 mt-12">
            {["LinkedIn", "Indeed", "Glassdoor", "Wellfound", "Naukri", "+8 more"].map(p => (
              <span key={p} className="text-sm text-white/40 font-medium">{p}</span>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Stats */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {STATS.map((s, i) => (
            <motion.div key={s.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 + 0.3 }}
              className="glass p-6 text-center">
              <div className="text-4xl font-black gradient-text mb-1">{s.value}</div>
              <div className="text-sm text-white/50">{s.label}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 py-16">
        <h2 className="text-4xl font-bold text-center mb-3">Everything Automated</h2>
        <p className="text-center text-white/50 mb-12 text-lg">From discovery to offer — your agent handles it all</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {FEATURES.map((f, i) => (
            <motion.div key={f.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
              className="glass glass-hover p-8">
              <div className="w-12 h-12 rounded-xl bg-indigo-500/20 flex items-center justify-center mb-5">
                <f.icon size={24} className="text-indigo-400" />
              </div>
              <h3 className="text-xl font-bold mb-3">{f.title}</h3>
              <p className="text-white/55 text-sm leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 py-16">
        <h2 className="text-4xl font-bold text-center mb-3">Simple Pricing</h2>
        <p className="text-center text-white/50 mb-12">Start free, upgrade when you land interviews</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { plan: "Free", price: "$0", features: ["20 applications/mo", "5 cold emails/mo", "1 platform", "Basic resume tailoring"], cta: "Get Started", highlight: false },
            { plan: "Pro", price: "$29", period: "/mo", features: ["Unlimited applications", "All 13+ platforms", "Cold email sequences", "Interview scheduling", "Residential proxy included", "Priority support"], cta: "Start Pro Trial", highlight: true },
            { plan: "Team", price: "$99", period: "/mo", features: ["5 user seats", "Shared templates", "Recruiter CRM", "Team analytics", "API access"], cta: "Contact Sales", highlight: false },
          ].map(tier => (
            <div key={tier.plan} className={`glass p-8 relative ${tier.highlight ? "border-indigo-500/40 glow-indigo" : ""}`}>
              {tier.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-indigo-600 rounded-full text-xs font-bold">MOST POPULAR</div>
              )}
              <div className="text-lg font-semibold text-white/70 mb-2">{tier.plan}</div>
              <div className="text-5xl font-black mb-1">{tier.price}<span className="text-lg font-normal text-white/40">{tier.period}</span></div>
              <div className="h-px bg-white/08 my-6" />
              <ul className="space-y-3 mb-8">
                {tier.features.map(f => (
                  <li key={f} className="flex items-start gap-2 text-sm text-white/70">
                    <CheckCircle2 size={16} className="text-indigo-400 mt-0.5 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <SignUpButton mode="modal">
                <button className={tier.highlight ? "btn-primary w-full py-3" : "btn-ghost w-full py-3"}>
                  {tier.cta}
                </button>
              </SignUpButton>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/08 mt-16 py-8 px-6 text-center text-white/30 text-sm space-y-2">
        <p>© 2025 AutoApply Pro. Automated activity may violate third-party ToS — all risk is borne by the user.</p>
        <p className="flex items-center justify-center gap-4">
          <Link href="/terms" className="hover:text-white/60 transition-colors">Terms of Service</Link>
          <span>·</span>
          <Link href="/privacy" className="hover:text-white/60 transition-colors">Privacy Policy</Link>
        </p>
      </footer>
    </div>
  );
}
