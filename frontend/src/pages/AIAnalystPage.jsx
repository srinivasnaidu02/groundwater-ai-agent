import React, { useState, useEffect, useCallback, useRef } from 'react';
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

    // Check if query is a comparison or contains explicit location references
    const qLower = trimmedQuery.toLowerCase();
    const isComparison = [
      'compare', 'comparison', 'between', ' vs ', ' vs. ', ' versus ',
      'difference', 'all states', 'across india', 'national', 'country-wide',
      'which states', 'highest', 'lowest', 'rank', 'top states', 'state-wise'
    ].some((kw) => qLower.includes(kw));

    const mentionsKnownState = states.some((s) => s && qLower.includes(s.toLowerCase()));

    // State is only required if the query does NOT compare locations AND does NOT mention any state
    if (!selectedState && !isComparison && !mentionsKnownState) {
      errors.state = 'State is required unless comparing locations or specified in your question.';
    }

    if (!trimmedQuery) {
      errors.query = 'Please enter your natural-language question.';
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setValidationError(
        errors.query
          ? 'Please enter your question before submitting.'
          : errors.state
          ? 'Please select a State / UT or mention a location in your question.'
          : 'Please complete all required fields before submitting.'
      );
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
        state: selectedState || null,
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
