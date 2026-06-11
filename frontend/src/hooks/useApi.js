import { useState, useEffect, useCallback } from 'react';

function extractErrorMessage(err) {
  const detail = err.response?.data?.detail;
  if (detail) {
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => (typeof d === 'object' ? d.msg || JSON.stringify(d) : String(d))).join('; ');
    }
    if (typeof detail === 'object') return detail.msg || JSON.stringify(detail);
  }
  return err.response?.data?.message || err.message || 'An unexpected error occurred';
}

/**
 * Generic hook for fetching data from an API function.
 * Returns { data, loading, error, refetch }.
 *
 * @param {Function} apiFn  — An axios function that returns a promise, e.g. () => fetchStudents()
 * @param {Array}    deps   — Dependency array to trigger refetch
 * @param {Object}   opts   — { immediate: boolean } whether to fetch on mount (default true)
 */
export default function useApi(apiFn, deps = [], opts = {}) {
  const { immediate = true } = opts;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFn();
      setData(res.data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    if (immediate) fetch();
  }, [fetch, immediate]);

  return { data, loading, error, refetch: fetch };
}
