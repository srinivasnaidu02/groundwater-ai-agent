import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Cpu } from 'lucide-react';
import {
  queryAgent,
  getAgentStatus,
  getMetaYears,
  getMetaStates,
  getMetaDistricts,
} from '../services/api';
import InfoHeader from '../components/analyst/InfoHeader';
import ContextSelectors from '../components/analyst/ContextSelectors';
import QuestionForm from '../components/analyst/QuestionForm';
import ExamplesPanel from '../components/analyst/ExamplesPanel';
import ResultsView from '../components/analyst/ResultsView';

export default function AIAnalystPage() {
  // Guided Context State
  const [years, setYears] = useState(['2025', '2026', '2024', '2023', '2022', '2020']);
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [selectedYear, setSelectedYear] = useState('2025');
  const [selectedState, setSelectedState] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');

  // Dropdown loading & error states
  const [loadingYears, setLoadingYears] = useState(false);
  const [loadingStates, setLoadingStates] = useState(false);
  const [loadingDistricts, setLoadingDistricts] = useState(false);
  const [errorStates, setErrorStates] = useState(false);

  // Query & Execution State
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('auto'); // 'auto' | 'agentic' | 'template'
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [validationError, setValidationError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});

  // Request ID / Abort guard to cancel stale district requests
  const districtRequestId = useRef(0);
  const resultsRef = useRef(null);

  // Fetch initial metadata: years and states
  const fetchMetadata = useCallback(async (yearToFetch = selectedYear) => {
    setLoadingYears(true);
    setLoadingStates(true);
    setErrorStates(false);

    let activeYear = yearToFetch;
    try {
      const yearsRes = await getMetaYears();
      const loadedYears = yearsRes.data?.years || yearsRes.data?.assessment_years || [];
      if (loadedYears.length > 0) {
        setYears(loadedYears);
        if (!loadedYears.includes(activeYear)) {
          activeYear = loadedYears.includes('2025') ? '2025' : loadedYears[0];
          setSelectedYear(activeYear);
        }
      }
    } catch (e) {
      console.warn('Could not load assessment years from meta endpoint:', e);
    } finally {
      setLoadingYears(false);
    }

    try {
      const statesRes = await getMetaStates(activeYear);
      const loadedStates = statesRes.data?.states || [];
      setStates(loadedStates);
    } catch (e) {
      console.error('Could not load states from meta endpoint:', e);
      setErrorStates(true);
    } finally {
      setLoadingStates(false);
    }
  }, [selectedYear]);

  // Fetch Agent Status
  const fetchStatus = useCallback(async () => {
    try {
      const res = await getAgentStatus();
      setStatus(res.data);
    } catch (e) {
      console.warn('Could not fetch agent status', e);
    }
  }, []);

  useEffect(() => {
    fetchMetadata();
    fetchStatus();
  }, [fetchMetadata, fetchStatus]);

  // Handle Year Change -> dynamically filter states and districts by selected year
  const handleYearChange = async (newYear) => {
    setSelectedYear(newYear);
    setFieldErrors((prev) => ({ ...prev, year: '' }));
    setValidationError('');

    setLoadingStates(true);
    setErrorStates(false);
    try {
      const res = await getMetaStates(newYear);
      const loadedStates = res.data?.states || [];
      setStates(loadedStates);

      // If selected state is no longer in the loaded states for this year, reset state and district
      if (selectedState && !loadedStates.includes(selectedState)) {
        setSelectedState('');
        setSelectedDistrict('');
        setDistricts([]);
      } else if (selectedState) {
        // State is still valid for this year; refresh districts for (state, newYear)
        const currentReqId = ++districtRequestId.current;
        setLoadingDistricts(true);
        try {
          const distRes = await getMetaDistricts(selectedState, newYear);
          if (currentReqId === districtRequestId.current) {
            const loadedDists = distRes.data?.districts || [];
            setDistricts(loadedDists);
            if (selectedDistrict && !loadedDists.includes(selectedDistrict)) {
              setSelectedDistrict('');
            }
          }
        } catch (err) {
          if (currentReqId === districtRequestId.current) {
            console.error(`Error loading districts for ${selectedState} in ${newYear}:`, err);
            setDistricts([]);
            setSelectedDistrict('');
          }
        } finally {
          if (currentReqId === districtRequestId.current) {
            setLoadingDistricts(false);
          }
        }
      }
    } catch (e) {
      console.error(`Error loading states for year ${newYear}:`, e);
      setErrorStates(true);
    } finally {
      setLoadingStates(false);
    }
  };

  // Handle State Change -> fetch districts with stale-response protection
  const handleStateChange = async (newState) => {
    setSelectedState(newState);
    setSelectedDistrict(''); // reset to state-level
    setDistricts([]);
    setFieldErrors((prev) => ({ ...prev, state: '' }));
    setValidationError('');

    if (!newState) return;

    const currentReqId = ++districtRequestId.current;
    setLoadingDistricts(true);

    try {
      const res = await getMetaDistricts(newState, selectedYear);
      // Only commit if this request is still the latest one
      if (currentReqId === districtRequestId.current) {
        setDistricts(res.data?.districts || []);
      }
    } catch (err) {
      if (currentReqId === districtRequestId.current) {
        console.error(`Error loading districts for ${newState}:`, err);
        setDistricts([]);
      }
    } finally {
      if (currentReqId === districtRequestId.current) {
        setLoadingDistricts(false);
      }
    }
  };

  // Handle Example Selection
  const handleSelectExample = async (ex) => {
    setQuery(ex.text);
    setValidationError('');
    setFieldErrors({});

    const targetYear = ex.year || selectedYear;
    if (ex.year && ex.year !== selectedYear) {
      setSelectedYear(ex.year);
    }

    if (ex.state) {
      setSelectedState(ex.state);
      // Ensure states list for targetYear is updated if year changed
      if (ex.year && ex.year !== selectedYear) {
        try {
          const stRes = await getMetaStates(ex.year);
          setStates(stRes.data?.states || []);
        } catch (err) {
          console.warn('Error loading states for example year:', err);
        }
      }

      const currentReqId = ++districtRequestId.current;
      setLoadingDistricts(true);
      try {
        const res = await getMetaDistricts(ex.state, targetYear);
        if (currentReqId === districtRequestId.current) {
          const loadedDists = res.data?.districts || [];
          setDistricts(loadedDists);
          if (ex.district && loadedDists.includes(ex.district)) {
            setSelectedDistrict(ex.district);
          } else {
            setSelectedDistrict('');
          }
        }
      } catch (e) {
        console.warn('Error loading districts for example:', e);
      } finally {
        if (currentReqId === districtRequestId.current) {
          setLoadingDistricts(false);
        }
      }
    }
  };

  // Handle Query Submission
  const handleSubmit = async () => {
    const trimmedQuery = query.trim();
    const errors = {};

    if (!selectedYear) {
      errors.year = 'Assessment year is required.';
    }
    if (!selectedState) {
      errors.state = 'State / Union Territory is required.';
    }
    if (!trimmedQuery) {
      errors.query = 'Please enter your natural-language question.';
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setValidationError('Please complete all required fields (Year, State, Question) before submitting.');
      return;
    }

    setFieldErrors({});
    setValidationError('');
    setLoading(true);
    setError(null);

    // Smooth scroll to results area
    if (resultsRef.current) {
      resultsRef.current.scrollIntoView({ behavior: 'smooth' });
    }

    try {
      const payload = {
        query: trimmedQuery,
        mode,
        year: selectedYear ? parseInt(selectedYear, 10) : null,
        state: selectedState,
        district: selectedDistrict || null,
      };

      const response = await queryAgent(payload);
      setResult(response.data);
    } catch (err) {
      console.error('Agent query failed:', err);
      const detailMsg =
        err.response?.data?.detail ||
        err.message ||
        'Network or server error executing query. Please try again.';
      setError(detailMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a1628] text-slate-100 py-6 sm:py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-5">
        {/* a) Header Card with 4px Teal Left Border */}
        <InfoHeader />

        {/* g) Mode Toggle & Active Provider Chip (Compact Row between Header and Form) */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-1">
          <div className="inline-flex bg-[#0b1a2d] p-1 rounded-lg border border-slate-800 text-xs">
            <button
              type="button"
              onClick={() => setMode('auto')}
              className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                mode === 'auto'
                  ? 'bg-teal-500 text-slate-950 font-semibold shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Auto (Intelligent)
            </button>
            <button
              type="button"
              onClick={() => setMode('agentic')}
              className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                mode === 'agentic'
                  ? 'bg-teal-500 text-slate-950 font-semibold shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Agentic (ReAct)
            </button>
            <button
              type="button"
              onClick={() => setMode('template')}
              className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                mode === 'template'
                  ? 'bg-teal-500 text-slate-950 font-semibold shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Template
            </button>
          </div>

          {status && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0b1a2d] border border-slate-800 text-xs text-slate-300">
              <Cpu className="w-3.5 h-3.5 text-teal-400" />
              <span className="font-mono text-slate-200">{status.model || 'gemini-2.5-flash'}</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  status.key_configured ? 'bg-emerald-400' : 'bg-amber-400'
                }`}
                title={status.key_configured ? 'Provider key active' : 'Running in offline/mock mode'}
              />
            </div>
          )}
        </div>

        {/* b & c) Guided Context Selectors */}
        <div className="bg-[#0f1f33] rounded-lg p-5 border border-slate-800/80 shadow-md">
          <ContextSelectors
            years={years}
            states={states}
            districts={districts}
            selectedYear={selectedYear}
            selectedState={selectedState}
            selectedDistrict={selectedDistrict}
            onYearChange={handleYearChange}
            onStateChange={handleStateChange}
            onDistrictChange={(d) => setSelectedDistrict(d)}
            loadingYears={loadingYears}
            loadingStates={loadingStates}
            loadingDistricts={loadingDistricts}
            errorStates={errorStates}
            onRetryStates={() => fetchMetadata(selectedYear)}
            validationErrors={fieldErrors}
          />
        </div>

        {/* d) "Your Question *" Card with Submit Button */}
        <QuestionForm
          query={query}
          onQueryChange={(q) => {
            setQuery(q);
            setFieldErrors((prev) => ({ ...prev, query: '' }));
            setValidationError('');
          }}
          onSubmit={handleSubmit}
          loading={loading}
          validationError={validationError}
        />

        {/* e) Collapsible Example Questions Panel */}
        <ExamplesPanel onSelectExample={handleSelectExample} />

        {/* f) RESULTS Area (hidden until first submit / loading / error) */}
        <div ref={resultsRef}>
          {(loading || error || result) && (
            <ResultsView result={result} loading={loading} error={error} />
          )}
        </div>
      </div>
    </div>
  );
}
