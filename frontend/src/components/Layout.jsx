import React, { useState } from 'react';
import { Menu } from 'lucide-react';
import Sidebar from './Sidebar';

export default function Layout({ children }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#07131e] text-slate-100 flex flex-col font-sans">
      <Sidebar
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
      />

      {/* Floating mobile toggle button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="lg:hidden fixed top-3 left-3 z-40 p-2 rounded-lg bg-[#07131e]/90 border border-slate-800 text-slate-300 hover:text-white"
        title="Open menu"
      >
        <Menu className="w-5 h-5" />
      </button>

      <div className={`flex-1 flex flex-col transition-all duration-200 ${collapsed ? 'lg:pl-16' : 'lg:pl-60'}`}>
        <main className="flex-1 overflow-x-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}
