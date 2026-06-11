import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, ChevronUp, ChevronDown, ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import { fetchStudents } from '../services/api';
import { SkeletonTable } from '../components/shared/Skeleton';
import ErrorState from '../components/shared/ErrorState';

const BANDS = ['all', 'low', 'medium', 'high', 'critical'];
const PAGE_SIZE = 20;

export default function StudentsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialSearch = searchParams.get('search') || '';
  
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState(initialSearch);
  const [bandFilter, setBandFilter] = useState('all');
  const [sortKey, setSortKey] = useState('risk_score');
  const [sortDir, setSortDir] = useState('desc');
  const [page, setPage] = useState(1);

  // Sync state if URL changes directly
  useEffect(() => {
    const urlSearch = searchParams.get('search') || '';
    if (urlSearch !== search) {
      setSearch(urlSearch);
    }
  }, [searchParams]);

  // Update URL when search state changes locally
  const handleSearchChange = (e) => {
    const val = e.target.value;
    setSearch(val);
    if (val) {
      setSearchParams({ search: val });
    } else {
      setSearchParams({});
    }
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchStudents({ search: search || undefined });
      setStudents(Array.isArray(res.data) ? res.data : res.data?.students || []);
    } catch (err) {
      setError(
        err.response?.data?.detail || err.message || 'Failed to load students'
      );
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadData();
    }, 300);
    return () => clearTimeout(timer);
  }, [loadData]);

  const filtered = useMemo(() => {
    let list = [...students];

    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (s) =>
          String(s.original_id || s.id || '').toLowerCase().includes(q) ||
          (s.anon_id || '').toLowerCase().includes(q)
      );
    }

    if (bandFilter !== 'all') {
      list = list.filter((s) => (s.risk_band || '').toLowerCase() === bandFilter);
    }

    list.sort((a, b) => {
      const aVal = a[sortKey] ?? 0;
      const bVal = b[sortKey] ?? 0;
      if (typeof aVal === 'string') {
        return sortDir === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
    });

    return list;
  }, [students, search, bandFilter, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  useEffect(() => {
    setPage(1);
  }, [search, bandFilter]);

  const toggleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const SortIcon = ({ col }) => {
    if (sortKey !== col) return null;
    return sortDir === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />;
  };

  const columns = [
    { key: 'id', label: 'Student ID' },
    { key: 'attendance_rate', label: 'Attendance %' },
    { key: 'quiz_average', label: 'Quiz Avg %' },
    { key: 'assignment_submission_rate', label: 'Assignment %' },
    { key: 'risk_score', label: 'Risk Score' },
    { key: 'risk_band', label: 'Risk Band' },
    { key: 'actions', label: 'Actions', sortable: false },
  ];

  return (
    <div className="fade-in">
      {/* Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
        <div className="header-search">
          <Search />
          <input
            type="text"
            placeholder="Search by Student ID..."
            value={search}
            onChange={handleSearchChange}
          />
        </div>

        <div className="filter-bar" style={{ marginBottom: 0 }}>
          {BANDS.map((b) => (
            <button
              key={b}
              className={`filter-btn ${bandFilter === b ? 'active' : ''}`}
              onClick={() => setBandFilter(b)}
            >
              {b.charAt(0).toUpperCase() + b.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="glass-card-static">
        {loading ? (
          <SkeletonTable rows={10} cols={7} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadData} />
        ) : (
          <>
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    {columns.map((col) => (
                      <th
                        key={col.key}
                        className={sortKey === col.key ? 'sorted' : ''}
                        onClick={col.sortable !== false ? () => toggleSort(col.key) : undefined}
                        style={col.sortable === false ? { cursor: 'default' } : undefined}
                      >
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          {col.label}
                          <SortIcon col={col.key} />
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {paginated.map((s) => (
                    <tr key={s.id} onClick={() => navigate(`/students/${s.id}`)}>
                      <td>{s.original_id || s.id}</td>
                      <td>{s.attendance_rate != null ? `${Number(s.attendance_rate).toFixed(1)}%` : '—'}</td>
                      <td>{s.quiz_average != null ? `${Number(s.quiz_average).toFixed(1)}%` : '—'}</td>
                      <td>{s.assignment_submission_rate != null ? `${Number(s.assignment_submission_rate).toFixed(1)}%` : '—'}</td>
                      <td>
                        <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                          {s.risk_score != null ? Number(s.risk_score).toFixed(3) : '—'}
                        </span>
                      </td>
                      <td>
                        <span className={`risk-badge ${(s.risk_band || '').toLowerCase()}`}>
                          {s.risk_band || '—'}
                        </span>
                      </td>
                      <td>
                        <button
                          className="btn btn-secondary btn-sm btn-icon"
                          title="View Details"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/students/${s.id}`);
                          }}
                        >
                          <Eye size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {paginated.length === 0 && (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                        No students found matching your criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="pagination">
              <span className="pagination-info">
                Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of{' '}
                {filtered.length} students
              </span>
              <div className="pagination-controls">
                <button
                  className="pagination-btn"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  <ChevronLeft size={14} />
                </button>
                {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                  let pageNum;
                  if (totalPages <= 7) {
                    pageNum = i + 1;
                  } else if (page <= 4) {
                    pageNum = i + 1;
                  } else if (page >= totalPages - 3) {
                    pageNum = totalPages - 6 + i;
                  } else {
                    pageNum = page - 3 + i;
                  }
                  return (
                    <button
                      key={pageNum}
                      className={`pagination-btn ${page === pageNum ? 'active' : ''}`}
                      onClick={() => setPage(pageNum)}
                    >
                      {pageNum}
                    </button>
                  );
                })}
                <button
                  className="pagination-btn"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
