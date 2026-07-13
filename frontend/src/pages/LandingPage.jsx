import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, Zap, Shield, Search } from "lucide-react";
import { AgentFlow } from "../components/AgentFlow";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans transition-colors duration-300">
      
      {/* Navbar */}
      <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="bg-blue-600 text-white p-1.5 rounded-lg">
            <Search className="w-5 h-5" />
          </div>
          <span className="font-bold text-xl tracking-tight">ShopBuddy AI</span>
        </div>
        <div className="hidden md:flex gap-8 font-medium text-slate-600 dark:text-slate-300">
          <a href="#features" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Features</a>
          <a href="#how-it-works" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">How it works</a>
          <a href="#pricing" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Pricing</a>
        </div>
        <div>
          <Link to="/app" className="bg-slate-900 dark:bg-white text-white dark:text-slate-900 px-5 py-2.5 rounded-full font-medium hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors">
            Go to App
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-24 pb-16 px-6 max-w-5xl mx-auto text-center">
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8 leading-tight">
          Smarter shopping, <br className="hidden md:block" />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-violet-600">explained simply.</span>
        </h1>
        <p className="text-lg md:text-xl text-slate-600 dark:text-slate-400 mb-10 max-w-3xl mx-auto leading-relaxed">
          The only Explainable AI Shopping Assistant that searches Amazon and Daraz simultaneously, compares products, and explicitly tells you <em>why</em> it recommends what you should buy.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <Link to="/app" className="group flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 rounded-full font-semibold text-lg transition-all shadow-lg shadow-blue-500/30">
            Start Shopping for Free
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </Link>
          <a href="#how-it-works" className="text-slate-600 dark:text-slate-300 font-medium hover:text-slate-900 dark:hover:text-white px-6 py-4">
            See how it works
          </a>
        </div>
      </section>

      {/* Logos Section */}
      <section className="py-10 border-y border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6">
          <p className="text-center text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-6">
            Searching products across top platforms
          </p>
          <div className="flex justify-center items-center gap-12 md:gap-24 opacity-60 grayscale hover:grayscale-0 transition-all duration-500">
            <img 
              src="https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg" 
              alt="Amazon" 
              className="h-8 md:h-10 dark:invert" 
            />
            <img 
              src="/images/Daraz-logo.png" 
              alt="Daraz" 
              className="h-8 md:h-10 object-contain w-auto" 
            />
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 px-6 max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Everything you need to make the right choice</h2>
          <p className="text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">We process thousands of reviews, specifications, and prices so you don't have to.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-white dark:bg-slate-900 p-8 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="bg-blue-100 dark:bg-blue-900/50 w-12 h-12 rounded-xl flex items-center justify-center mb-6">
              <Zap className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <h3 className="text-xl font-bold mb-3">Explainable Reasoning</h3>
            <p className="text-slate-600 dark:text-slate-400">Our AI doesn't just give you a product. It provides step-by-step reasoning on why it fits your specific query.</p>
          </div>
          <div className="bg-white dark:bg-slate-900 p-8 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="bg-violet-100 dark:bg-violet-900/50 w-12 h-12 rounded-xl flex items-center justify-center mb-6">
              <Search className="w-6 h-6 text-violet-600 dark:text-violet-400" />
            </div>
            <h3 className="text-xl font-bold mb-3">Cross-platform Search</h3>
            <p className="text-slate-600 dark:text-slate-400">Simultaneously search Amazon and Daraz. We handle the currency conversions and spec comparisons automatically.</p>
          </div>
          <div className="bg-white dark:bg-slate-900 p-8 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="bg-green-100 dark:bg-green-900/50 w-12 h-12 rounded-xl flex items-center justify-center mb-6">
              <Shield className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-xl font-bold mb-3">Save History</h3>
            <p className="text-slate-600 dark:text-slate-400">Keep track of your previous searches and favorite products. Pick up exactly where you left off.</p>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-24 px-6 bg-slate-100 dark:bg-slate-900/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">How our Agents work together</h2>
            <p className="text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
              Our multi-agent architecture breaks down your request, searches multiple sources, reviews the data, and formulates an easy-to-understand response.
            </p>
          </div>
          <AgentFlow />
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-24 px-6 max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Simple, transparent pricing</h2>
          <p className="text-slate-600 dark:text-slate-400">Start for free, upgrade when you need more power.</p>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Free Tier */}
          <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
            <h3 className="text-2xl font-bold mb-2">Free Trial</h3>
            <p className="text-slate-500 dark:text-slate-400 mb-6">Perfect for testing the waters.</p>
            <div className="mb-8">
              <span className="text-5xl font-extrabold">$0</span>
              <span className="text-slate-500 dark:text-slate-400">/one-time</span>
            </div>
            <ul className="space-y-4 mb-8 flex-1">
              <li className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-blue-600" />
                <span>1 free AI shopping query</span>
              </li>
              <li className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-blue-600" />
                <span>Access to both Amazon & Daraz</span>
              </li>
              <li className="flex items-center gap-3 text-slate-400">
                <CheckCircle2 className="w-5 h-5" />
                <span>Save favorite products</span>
              </li>
            </ul>
            <Link to="/app" className="w-full py-4 rounded-xl font-semibold text-center bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
              Get Started for Free
            </Link>
          </div>

          {/* Pro Tier */}
          <div className="bg-blue-600 text-white rounded-3xl p-8 shadow-xl shadow-blue-900/20 relative flex flex-col transform md:-translate-y-4">
            <div className="absolute top-0 right-8 transform -translate-y-1/2">
              <span className="bg-gradient-to-r from-amber-400 to-orange-500 text-white text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                Most Popular
              </span>
            </div>
            <h3 className="text-2xl font-bold mb-2">Pro Plan</h3>
            <p className="text-blue-100 mb-6">For the smart, frequent shopper.</p>
            <div className="mb-8">
              <span className="text-5xl font-extrabold">$10</span>
              <span className="text-blue-200">/month</span>
            </div>
            <ul className="space-y-4 mb-8 flex-1">
              <li className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-blue-200" />
                <span>Unlimited AI shopping queries</span>
              </li>
              <li className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-blue-200" />
                <span>Priority agent processing speed</span>
              </li>
              <li className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-blue-200" />
                <span>Unlimited saved favorite products</span>
              </li>
              <li className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-blue-200" />
                <span>Extended search history</span>
              </li>
            </ul>
            <Link to="/app" className="w-full py-4 rounded-xl font-semibold text-center bg-white text-blue-600 hover:bg-slate-50 transition-colors">
              Upgrade to Pro
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 py-12 bg-white dark:bg-slate-950">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <Search className="w-5 h-5 text-blue-600" />
            <span className="font-bold text-lg">ShopBuddy AI</span>
          </div>
          <div className="flex gap-8 text-sm text-slate-500 dark:text-slate-400">
            <Link to="/legal" className="hover:text-slate-900 dark:hover:text-white transition-colors">Terms of Service</Link>
            <Link to="/legal" className="hover:text-slate-900 dark:hover:text-white transition-colors">Privacy Policy</Link>
            <a href="#" className="hover:text-slate-900 dark:hover:text-white transition-colors">Contact</a>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            &copy; {new Date().getFullYear()} ShopBuddy AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
