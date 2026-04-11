import Link from 'next/link';
import { Bot } from 'lucide-react';

export const metadata = {
  title: 'Privacy Policy — AutoApply Pro',
  description: 'AutoApply Pro Privacy Policy. How we collect, store, and protect your data.',
};

export default function PrivacyPage() {
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
        <h1 className="text-4xl font-black mb-2">Privacy Policy</h1>
        <p className="text-white/40 text-sm mb-10">Last updated: April 10, 2025</p>

        <div className="space-y-10 text-white/75 leading-relaxed">

          <section>
            <h2 className="text-xl font-bold text-white mb-3">1. Introduction</h2>
            <p>
              AutoApply Pro (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;) is committed to protecting your personal information. This Privacy Policy describes what data we collect, how we use it, and your rights over it.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">2. What Data We Collect</h2>
            <p className="mb-3">We collect the following categories of information:</p>

            <h3 className="font-semibold text-white mb-2">Account Information</h3>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Email address (used for authentication via Clerk and service notifications)</li>
              <li>Name (optional, used to personalize applications)</li>
            </ul>

            <h3 className="font-semibold text-white mb-2">Resume &amp; Profile Data</h3>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Resume / CV content you upload or enter</li>
              <li>Work experience, education, skills, and preferences</li>
              <li>Job preferences (target roles, locations, salary expectations)</li>
            </ul>

            <h3 className="font-semibold text-white mb-2">Platform Credentials</h3>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Usernames and passwords for job platforms (LinkedIn, Indeed, etc.) that you authorize the agent to use</li>
              <li><strong className="text-green-400">These are encrypted with AES-256</strong> and stored in HashiCorp Vault. We never read or expose your raw passwords.</li>
            </ul>

            <h3 className="font-semibold text-white mb-2">Usage &amp; Activity Data</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Application history, email send logs, agent action logs</li>
              <li>Browser session metadata (for anti-detection purposes — not linked to personal identity)</li>
              <li>IP address (for security and fraud prevention)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">3. How We Store &amp; Protect Your Data</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong className="text-white">Encryption at rest:</strong> All sensitive fields (credentials, resume content) are encrypted with AES-256 before storage.</li>
              <li><strong className="text-white">Encryption in transit:</strong> All API communication is over HTTPS/TLS 1.3.</li>
              <li><strong className="text-white">Secrets management:</strong> Platform credentials are stored in HashiCorp Vault with strict access controls and audit logging.</li>
              <li><strong className="text-white">Access controls:</strong> Only your active agent session can decrypt your credentials, minimizing the window of exposure.</li>
              <li><strong className="text-white">No sale of data:</strong> We do not sell, rent, or share your personal information with third parties for marketing purposes — ever.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">4. How We Use Your Data</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>To operate and personalize the AI job automation agent on your behalf</li>
              <li>To generate tailored resumes and cover letters for each application</li>
              <li>To send transactional emails (receipts, flag notifications, activity summaries)</li>
              <li>To improve service quality through aggregated, anonymized analytics</li>
              <li>To comply with legal obligations</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">5. Third-Party Services</h2>
            <p className="mb-3">We use the following sub-processors:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong className="text-white">Clerk</strong> — Authentication &amp; user identity management</li>
              <li><strong className="text-white">Anthropic (Claude)</strong> — AI-generated resume tailoring and email drafts</li>
              <li><strong className="text-white">Stripe</strong> — Billing and payment processing</li>
              <li><strong className="text-white">AWS</strong> — Cloud infrastructure (encrypted at rest)</li>
              <li><strong className="text-white">Bright Data</strong> — Residential proxy network for agent sessions</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">6. Your GDPR Rights</h2>
            <p className="mb-3">If you are located in the European Economic Area (EEA) or United Kingdom, you have the following rights:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong className="text-white">Right of access:</strong> Request a copy of the personal data we hold about you.</li>
              <li><strong className="text-white">Right to rectification:</strong> Correct inaccurate or incomplete personal data.</li>
              <li><strong className="text-white">Right to erasure (&quot;right to be forgotten&quot;):</strong> Request deletion of your data — we will process this within 30 days.</li>
              <li><strong className="text-white">Right to data portability:</strong> Receive your data in a machine-readable format.</li>
              <li><strong className="text-white">Right to restrict processing:</strong> Limit how we use your data in certain circumstances.</li>
              <li><strong className="text-white">Right to object:</strong> Object to processing based on legitimate interest.</li>
            </ul>
            <p className="mt-3">To exercise any of these rights, email <a href="mailto:privacy@autoapply.pro" className="text-indigo-400 hover:underline">privacy@autoapply.pro</a>. We will respond within 30 days.</p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">7. Data Retention</h2>
            <p>We retain your data for as long as your account is active. Upon account deletion, all personal data is permanently purged within 30 days, except where retention is required by law (e.g., billing records for 7 years).</p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">8. Cookies</h2>
            <p>We use essential session cookies (via Clerk) for authentication. We do not use third-party advertising cookies or tracking pixels.</p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">9. Children&apos;s Privacy</h2>
            <p>Our Service is not directed to individuals under the age of 18. We do not knowingly collect personal information from minors.</p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">10. Changes to This Policy</h2>
            <p>We may update this policy periodically. We will notify you via email at least 14 days before material changes take effect.</p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-3">11. Contact Us</h2>
            <p>
              For any privacy-related questions or requests, contact us at:
            </p>
            <div className="mt-3 glass p-4 rounded-xl text-sm">
              <p className="font-semibold text-white">AutoApply Pro — Privacy Team</p>
              <p>Email: <a href="mailto:privacy@autoapply.pro" className="text-indigo-400 hover:underline">privacy@autoapply.pro</a></p>
              <p className="text-white/40 mt-1">Response time: within 30 days for GDPR requests, typically faster for general enquiries</p>
            </div>
          </section>

        </div>
      </main>

      <footer className="relative z-10 border-t border-white/08 mt-16 py-8 px-6 text-center text-white/30 text-sm">
        <p>© 2025 AutoApply Pro · <Link href="/privacy" className="hover:text-white/60 transition-colors">Privacy Policy</Link> · <Link href="/terms" className="hover:text-white/60 transition-colors">Terms of Service</Link></p>
      </footer>
    </div>
  );
}
