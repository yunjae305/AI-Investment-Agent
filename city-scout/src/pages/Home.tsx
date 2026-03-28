import React from 'react';
import { Map, Zap, Sun, ArrowRight, Globe } from 'lucide-react';
import { Link } from 'react-router-dom';

const Home = () => {
  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="bg-white border-b border-zinc-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <Globe className="w-8 h-8 text-emerald-600" />
              <span className="text-xl font-bold text-zinc-900 tracking-tight">CityScout</span>
            </div>
            <nav className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm font-medium text-zinc-600 hover:text-emerald-600 transition-colors">Features</a>
              <Link to="/login" className="px-4 py-2 text-sm font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-all shadow-sm">Get Started</Link>
            </nav>
          </div>
        </div>
      </header>

      <main>
        <section className="relative py-20 overflow-hidden">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <h1 className="text-5xl md:text-6xl font-extrabold text-zinc-900 mb-6 tracking-tight">
                Build a Better City with <span className="text-emerald-600">Minecraft Intelligence</span>
              </h1>
              <p className="text-xl text-zinc-600 mb-10 max-w-3xl mx-auto leading-relaxed">
                Transform real-world urban data into immersive 3D simulations. Analyze accessibility and solar impact with the power of Arnis and Minecraft. 
              </p>
              <div className="flex justify-center gap-4">
                <Link to="/upload" className="px-8 py-4 bg-emerald-600 text-white font-semibold rounded-xl hover:bg-emerald-700 transition-all shadow-lg flex items-center gap-2">
                  Start Analysis <ArrowRight className="w-5 h-5" />
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

export default Home;
