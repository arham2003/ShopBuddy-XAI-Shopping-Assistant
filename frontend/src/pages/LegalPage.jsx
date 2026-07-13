import React, { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowLeft, Search } from "lucide-react";

export default function LegalPage() {
  const { hash } = useLocation();

  useEffect(() => {
    if (hash) {
      const element = document.getElementById(hash.substring(1));
      if (element) {
        element.scrollIntoView({ behavior: "smooth" });
      }
    } else {
      window.scrollTo(0, 0);
    }
  }, [hash]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans transition-colors duration-300">
      
      {/* Navbar Minimal */}
      <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <div className="bg-blue-600 text-white p-1.5 rounded-lg">
            <Search className="w-5 h-5" />
          </div>
          <span className="font-bold text-xl tracking-tight">ShopBuddy AI</span>
        </div>
        <Link to="/" className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Home
        </Link>
      </nav>

      {/* Main Content Area */}
      <div className="max-w-7xl mx-auto px-6 py-16 flex flex-col md:flex-row gap-12 lg:gap-24">
        
        {/* Sticky Sidebar */}
        <aside className="md:w-64 flex-shrink-0">
          <div className="sticky top-16">
            <h2 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-4">Legal</h2>
            <nav className="flex flex-col gap-2">
              <a 
                href="#terms" 
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${hash === '#terms' || !hash ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900'}`}
              >
                Terms of Service
              </a>
              <a 
                href="#privacy" 
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${hash === '#privacy' ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900'}`}
              >
                Privacy Policy
              </a>
            </nav>

            <div className="mt-12 p-6 bg-slate-100 dark:bg-slate-900 rounded-2xl">
              <h3 className="text-sm font-semibold mb-2">Have a question?</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                Reach out to our support team and we'll get back to you.
              </p>
              <a href="mailto:support@shopbuddy.com" className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline">
                support@shopbuddy.com
              </a>
            </div>
          </div>
        </aside>

        {/* Legal Text */}
        <main className="flex-1 max-w-3xl prose prose-slate dark:prose-invert prose-headings:font-bold prose-h1:text-4xl prose-h2:text-2xl prose-a:text-blue-600 dark:prose-a:text-blue-400">
          <div>
            <h1 className="mb-2">Legal & Privacy Policy</h1>
            <p className="text-slate-500 dark:text-slate-400 mt-0 mb-12">
              Last updated: {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
            </p>

            <div id="terms" className="scroll-mt-16">
              <h2>1. Terms of Service</h2>
              <p>
                Welcome to ShopBuddy AI. By accessing or using our website, application, and services, you agree to comply with and be bound by these Terms of Service. If you do not agree to these terms, please do not use our services.
              </p>
              <h3>1.1 Use of the Service</h3>
              <p>
                ShopBuddy AI provides explainable AI shopping recommendations by aggregating data from external platforms such as Amazon and Daraz. Our service is intended for personal, non-commercial use.
              </p>
              <h3>1.2 Third-Party Links</h3>
              <p>
                Our service contains links to third-party e-commerce websites. We are not responsible for the content, privacy policies, or practices of any third-party sites.
              </p>
            </div>

            <hr className="my-12 border-slate-200 dark:border-slate-800" />

            <div id="privacy" className="scroll-mt-16">
              <h2>2. Privacy Policy</h2>
              <p>
                At ShopBuddy AI, we take your privacy seriously. This section outlines how we handle the information provided during your use of our service.
              </p>
              <h3>2.1 Data Collection & AI Usage</h3>
              <p className="font-medium bg-blue-50 dark:bg-blue-900/20 p-4 rounded-xl border border-blue-100 dark:border-blue-900 text-slate-800 dark:text-slate-200">
                None of your data is accessed by us. However, your data is used by 3rd party AI providers to fulfill your shopping needs. We are not responsible if any of your data is used by AI providers for other purposes like model training, etc.
              </p>
              <h3>2.2 Personal Information Protection</h3>
              <p>
                Your personal info, like your email address or account details, is <strong>not shared</strong> with any 3rd party services. We only transmit the necessary shopping query constraints to our upstream providers to fetch relevant products.
              </p>
              <h3>2.3 Changes to this Policy</h3>
              <p>
                We may update our Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page.
              </p>
            </div>
          </div>
        </main>
      </div>

      {/* Footer minimal */}
      <footer className="border-t border-slate-200 dark:border-slate-800 py-8 bg-white dark:bg-slate-950 mt-12">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            &copy; {new Date().getFullYear()} ShopBuddy AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
