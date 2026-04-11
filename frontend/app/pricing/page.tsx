import Link from "next/link";
import { CheckCircle2, Zap, Shield, Globe, Mail, BarChart3, Bot, ArrowRight } from "lucide-react";

export const metadata = {
  title: "Pricing — AutoApply Pro",
  description: "Simple, transparent pricing. Start free, upgrade when you're ready.",
};

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    period: "forever",
    tagline: "Try it risk-free",
    highlight: false,
    cta: "Get Started Free",
    ctaHref: "/sign-up",
    features: [
      "20 applications / month",
      "5 cold emails / month",
      "1 job platform",
      "Basic resume tailoring",
      "Application tracker",
      "Community support",
    ],
    missing: [
      "Unlimited applications",
      "All 13+ platforms",
      "Cold email sequences",
      "Interview scheduling",
      "Residential proxy (stealth)",
      "Priority support",
    ],
  },
  {
    id: "pro",
    name: "Pro",
    price: "$29",
    period: "/ month",
    tagline: "For serious job seekers",
    highlight: true,
    cta: "Start Pro — 7-day free trial",
    ctaHref: "/api/billing/checkout?plan=pro",
    features: [
      "Unlimited applications",
      "All 13+ platforms (LinkedIn, Naukri, Indeed, Wellfound…)",
      "Unlimited cold email sequences",
      "AI-powered cover letters",
      "ATS-optimized resume tailoring",
      "Interview scheduling assistant",
      "Residential proxy (anti-detection)",
      "Real-time dashboard + analytics",
      "Email open/reply tracking",
      "Priority support (< 4h response)",
    ],
    missing: [],
  },
  {
    id: "team",
    name: "Team",
    price: "$99",
    period: "/ month",
    tagline: "For agencies & placement firms",
    highlight: false,
    cta: "Contact Sales",
    ctaHref: "mailto:team@autoapplypro.ai",
    features: [
      "Everything in Pro",
      "5 candidate seats",
      "Centralized CRM dashboard",
      "Bulk resume upload",
      "White-label reports",
      "REST API access",
      "Dedicated account manager",
      "SLA: 99.9% uptime guarantee",
    ],
    missing: [],
  },
];

const FAQ = [
  {
    q: "Will platforms detect that I'm using a bot?",
    a: "AutoApply Pro uses residential proxies via Bright Data and realistic mouse-movement simulation, making activity indistinguishable from a human. We apply at a human pace (max 25–40 apps/day per platform) to avoid rate-limit flags.",
  },
  {
    q: "Do you store my platform passwords?",
    a: "No. We use browser session tokens, not passwords. Your credentials are never transmitted to our servers. Sessions are AES-256 encrypted and stored locally in encrypted form.",
  },
  {
    q: "Can I cancel at any time?",
    a: "Yes — cancel anytime from the billing settings. No cancellation fees. Your data is retained for 30 days after cancellation, then permanently deleted.",
  },
  {
    q: "What's the refund policy?",
    a: "Full refund within 7 days of purchase, no questions asked. After 7 days, refunds are discretionary based on usage.",
  },
  {
    q: "I'm in India — do you support Naukri?",
    a: "Yes. Naukri is one of our most-used platforms for Indian candidates. We also support Instahyre, Wellfound, and LinkedIn Jobs globally.",
  },
];

export default async function PricingPage() {
  return (
    <div className="min-h-screen">
      <div className="bg-mesh" />

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-5">
        <Link href="/" className="flex items-center gap-2 font-bold tracking-tight">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
            <Bot size={16} className="text-white" />
          </div>
          AutoApply Pro
        </Link>
        <div className="flex items-center gap-4">
          <Link href="/demo" className="text-sm text-white/60 hover:text-white transition-colors">Live Demo</Link>
          <Link href="/sign-in" className="btn-ghost text-sm py-2 px-4">Sign in</Link>
          <Link href="/sign-up" className="btn-primary text-sm py-2 px-4">Get Started Free</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 text-center pt-16 pb-12 px-4">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-sm font-medium mb-6">
          <Zap size={14} /> Simple, transparent pricing
        </div>
        <h1 className="text-4xl md:text-5xl font-black mb-4">
          Start free.{" "}
          <span className="gradient-text">Upgrade when ready.</span>
        </h1>
        <p className="text-white/50 text-lg max-w-xl mx-auto">
          No credit card required to start. 7-day free trial on Pro — cancel any time.
        </p>
      </section>

      {/* Plans */}
      <section className="relative z-10 max-w-6xl mx-auto px-6 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
          {PLANS.map(plan => (
            <div key={plan.id}
              className={`glass rounded-2xl p-8 flex flex-col gap-6 ${plan.highlight ? "border-indigo-500/40 glow-indigo relative" : "border-white/08"}`}>
              {plan.highlight && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1.5 rounded-full bg-indigo-500 text-white text-xs font-bold">
                  MOST POPULAR
                </div>
              )}
              <div>
                <h2 className="font-bold text-xl">{plan.name}</h2>
                <p className="text-white/40 text-sm mt-0.5">{plan.tagline}</p>
              </div>
              <div className="flex items-end gap-1">
                <span className={`text-5xl font-black ${plan.highlight ? "gradient-text" : ""}`}>{plan.price}</span>
                <span className="text-white/40 text-sm mb-1.5">{plan.period}</span>
              </div>

              {/* CTA */}
              <a href={plan.ctaHref}
                className={`w-full py-3 rounded-xl text-sm font-bold text-center transition-all ${plan.highlight ? "btn-primary" : "btn-ghost"}`}>
                {plan.cta}
              </a>

              {/* Features */}
              <ul className="space-y-2.5">
                {plan.features.map(f => (
                  <li key={f} className="flex items-start gap-2.5 text-sm text-white/80">
                    <CheckCircle2 size={15} className="text-green-400 shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
                {plan.missing.map(f => (
                  <li key={f} className="flex items-start gap-2.5 text-sm text-white/25 line-through">
                    <CheckCircle2 size={15} className="opacity-25 shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Trust badges */}
        <div className="flex flex-wrap justify-center gap-8 mt-14 text-white/40 text-sm">
          {[
            { icon: Shield, text: "AES-256 encrypted sessions" },
            { icon: Globe, text: "135+ country proxy coverage" },
            { icon: Mail, text: "SMTP email deliverability" },
            { icon: BarChart3, text: "Real-time analytics" },
          ].map(({ icon: Icon, text }) => (
            <div key={text} className="flex items-center gap-2">
              <Icon size={16} /> {text}
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="relative z-10 max-w-3xl mx-auto px-6 pb-24">
        <h2 className="text-2xl font-bold text-center mb-10">Frequently Asked Questions</h2>
        <div className="space-y-4">
          {FAQ.map(({ q, a }) => (
            <div key={q} className="glass p-6 rounded-xl">
              <h3 className="font-semibold text-sm mb-2">{q}</h3>
              <p className="text-white/50 text-sm leading-relaxed">{a}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="relative z-10 max-w-2xl mx-auto px-6 pb-24 text-center">
        <div className="glass p-10 rounded-2xl border border-indigo-500/20">
          <h2 className="text-3xl font-black mb-3">Ready to let AI handle<br />your job search?</h2>
          <p className="text-white/50 mb-8">Start free today. Your agent can apply to 50+ jobs before you finish breakfast.</p>
          <div className="flex gap-4 justify-center">
            <Link href="/sign-up">
              <button className="btn-primary px-8 py-3 text-base font-bold flex items-center gap-2">
                Start for Free <ArrowRight size={16} />
              </button>
            </Link>
            <Link href="/demo">
              <button className="btn-ghost px-8 py-3 text-base font-semibold">
                See the Dashboard
              </button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/08 py-8 text-center text-white/25 text-sm">
        <div className="flex justify-center gap-6 mb-3">
          <Link href="/terms" className="hover:text-white/60 transition-colors">Terms</Link>
          <Link href="/privacy" className="hover:text-white/60 transition-colors">Privacy</Link>
          <a href="mailto:support@autoapplypro.ai" className="hover:text-white/60 transition-colors">Contact</a>
        </div>
        <p>© 2026 AutoApply Pro. All rights reserved.</p>
      </footer>
    </div>
  );
}
