import React from 'react';
import { Link } from 'react-router-dom';
import { Globe, ArrowRight } from 'lucide-react';

const Login = () => {
  return (
    <div className="min-h-screen bg-zinc-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <Globe className="w-12 h-12 text-emerald-600" />
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-zinc-900">Sign in to CityScout</h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-xl border border-zinc-100 sm:rounded-2xl sm:px-10">
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-zinc-700">Email address</label>
              <input type="email" className="mt-1 block w-full border border-zinc-300 rounded-xl px-3 py-2 focus:ring-emerald-500 focus:border-emerald-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-700">Password</label>
              <input type="password" placeholder="••••••••" className="mt-1 block w-full border border-zinc-300 rounded-xl px-3 py-2 focus:ring-emerald-500 focus:border-emerald-500" />
            </div>
            <Link to="/" className="w-full flex justify-center py-3 bg-emerald-600 text-white font-semibold rounded-xl hover:bg-emerald-700 transition-all shadow-lg items-center gap-2">
              Sign in <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
