import Link from 'next/link';
import { Bot } from 'lucide-react';

export const metadata = {
  title: 'Terms of Service — AutoApply Pro',
  description: 'AutoApply Pro Terms of Service. Read before using our AI job application platform.',
};

export default function TermsPage() {
  return (
    <div className="min-h-screen">
      <div className="bg-mesh" />

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-6 py-5 max-w-4xl mx-auto">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
            <Bot size={18} className="text-white" />
          </div>
          <span className="font-bold text-lg tracking-tight">AutoApply Pro</span>
        </Link>
        <Link href="/" className="text-sm text-white/50 hover:text-white transition-colors">← Back to Home</Link>
      </nav>

      <main className="relative z-10 max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-4xl font-black mb-2">Terms of Service</h1>
        <p className="text-white/40 text-sm mb-10">Last updated: April 10, 2025</p>

        <div className="space-y-10 text-white/75 leading-relaxed">

          <section>
            <h2 className="text-xl font-bold text-white mb-3">1. Acceptance of Terms</h2>
            <p>By accessing or using AutoApply Pro (&quot;Service&quot;), you agree to be bound by these Terms of Service. If you do not agree, do not use the Service.</p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">2. Automated Activity &amp; Third-Party Platform Risk</h2>
            <p className="mb-3">
              <strong className="text-amber-400">⚠ Important notice:</strong> AutoApply Pro is an automation tool that interacts with third-party platforms such as LinkedIn, Indeed, Glassdoor, and others. Many of these platforms explicitly prohibit automated activity in their own Terms of Service.
            </p>
            <p className="mb-3">
              By using AutoApply Pro, you acknowledge and accept the following:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Automated activity performed on your behalf may violate the Terms of Service of third-party platforms.</li>
              <li>You assume <strong className="text-white">full responsibility</strong> for any consequences including, but not limited to, account restrictions, suspensions, or permanent bans imposed by third-party platforms.</li>
              <li>AutoApply Pro bears no liability for any action taken against your accounts on third-party platforms.</li>
              <li>You represent that you have read and understood the ToS of each platform you authorize the agent to access on your behalf.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">3. Account Registration</h2>
            <p>You must provide accurate, complete information when creating an account. You are responsible for maintaining the security of your credentials. Notify us immediately at <a href="mailto:support@autoapply.pro" className="text-indigo-400 hover:underline">support@autoapply.pro</a> if you suspect unauthorized access.</p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">4. Data Handling</h2>
            <p className="mb-3">We collect and store:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Your resume and profile information to tailor applications</li>
              <li>Credentials (stored encrypted — we never view your raw passwords; see our <Link href="/privacy" className="text-indigo-400 hover:underline">Privacy Policy</Link>)</li>
              <li>Application history, email records, and agent activity logs</li>
            </ul>
            <p className="mt-3">All data is stored with AES-256 encryption at rest. Your credentials are decrypted only in-memory during agent execution and are never persisted in plaintext.</p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">5. Subscription &amp; Billing</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong className="text-white">Free tier:</strong> Limited to 20 applications per month at no charge.</li>
              <li><strong className="text-white">Pro tier ($29/mo):</strong> Unlimited applications across all supported platforms. Billed monthly. Cancel anytime.</li>
              <li><strong className="text-white">Team tier ($99/mo):</strong> Up to 5 seats with shared templates and analytics. Billed monthly.</li>
              <li>Prices are subject to change with 30 days' notice to your registered email.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">6. Refund Policy</h2>
            <p className="mb-3">
              We offer <strong className="text-white">no refunds</strong> for partial billing periods. If you cancel your subscription, you retain access until the end of the current billing period.
            </p>
            <p>
              Exceptions may be made at our sole discretion for service-level failures caused by our platform. Refund requests must be submitted within 7 days of the charge to <a href="mailto:billing@autoapply.pro" className="text-indigo-400 hover:underline">billing@autoapply.pro</a>.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">7. Prohibited Use</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>Using the Service for fraudulent applications or misrepresentation</li>
              <li>Reselling or sublicensing access to our platform</li>
              <li>Attempting to reverse-engineer, scrape, or circumvent our own platform</li>
              <li>Violating any applicable laws or regulations</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">8. Disclaimer of Warranties</h2>
            <p>The Service is provided &quot;as is&quot; without warranties of any kind, express or implied. We do not guarantee interview outcomes, job placements, or specific application volumes. Platform availability and anti-detection effectiveness may vary.</p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">9. Limitation of Liability</h2>
            <p>To the fullest extent permitted by law, AutoApply Pro shall not be liable for indirect, incidental, consequential, or punitive damages arising from your use of the Service, including loss of employment opportunities or third-party platform actions.</p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">10. Governing Law</h2>
            <p>These Terms are governed by the laws of the State of Delaware, USA, without regard to conflict of law principles.</p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">11. Contact</h2>
            <p>Questions about these Terms? Email <a href="mailto:legal@autoapply.pro" className="text-indigo-400 hover:underline">legal@autoapply.pro</a>.</p>
          </section>

        </div>
      </main>

      <footer className="relative z-10 border-t border-white/08 mt-16 py-8 px-6 text-center text-white/30 text-sm">
        <p>© 2025 AutoApply Pro · <Link href="/privacy" className="hover:text-white/60 transition-colors">Privacy Policy</Link> · <Link href="/terms" className="hover:text-white/60 transition-colors">Terms of Service</Link></p>
      </footer>
    </div>
  );
}
