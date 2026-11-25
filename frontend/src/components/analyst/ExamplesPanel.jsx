import React, { useState } from 'react';
import { ChevronDown, ChevronUp, HelpCircle } from 'lucide-react';

export const EXAMPLE_QUESTIONS = [
  {
    text: "What are the groundwater assessment metrics for Hyderabad in 2025?",
    state: "Telangana",
    district: "Hyderabad",
    year: "2025",
  },
  {
    text: "Show the groundwater extraction stage for Pune in 2024.",
    state: "Maharashtra",
    district: "Pune",
    year: "2024",
  },
  {
    text: "Show the groundwater summary for Rajasthan in 2024.",
    state: "Rajasthan",
    district: "",
    year: "2024",
  },
  {
    text: "Compare groundwater extraction stage in Pune for 2022 and 2024.",
    state: "Maharashtra",
    district: "Pune",
    year: "2024",
  },
  {
    text: "Why is Ludhiana over-exploited and how did it change from 2020 to 2026?",
    state: "Punjab",
    district: "Ludhiana",
    year: "2025",
  },
  {
    text: "Compare groundwater extraction and recharge between Punjab and Haryana in 2025.",
    state: "",
    district: "",
    year: "2025",
  },
];

export default function ExamplesPanel({ onSelectExample }) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="bg-[#0f1f33] rounded-lg border border-slate-800/80 shadow-md overflow-hidden text-xs">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full px-5 py-3.5 flex items-center justify-between text-slate-200 hover:text-white hover:bg-slate-800/30 transition-all font-semibold"
      >
        <span className="flex items-center gap-2">
          <HelpCircle className="w-4 h-4 text-teal-400" />
          <span>Example Questions</span>
        </span>
        {isOpen ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>

      {isOpen && (
        <div className="px-5 pb-5 pt-1 border-t border-slate-800/60 bg-[#0c1a2b]/70 space-y-2">
          <p className="text-[11px] text-slate-400">
            Click any question below to automatically populate the input and select the matching assessment context:
          </p>
          <ul className="space-y-2 list-disc list-inside">
            {EXAMPLE_QUESTIONS.map((ex, idx) => (
              <li key={idx} className="text-slate-300">
                <button
                  type="button"
                  onClick={() => onSelectExample(ex)}
                  className="italic hover:text-teal-300 text-slate-300 text-left transition-colors cursor-pointer inline"
                >
                  "{ex.text}"
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
