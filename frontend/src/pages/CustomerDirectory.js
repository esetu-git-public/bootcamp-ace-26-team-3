import React, { useState, useEffect } from 'react';
import * as apiService from '../services/api';

export default function CustomerDirectory({ onViewChange, onSelectCustomer, onLogout }) {
  const [customers, setCustomers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters State
  const [searchId, setSearchId] = useState('');
  const [selectedRisk, setSelectedRisk] = useState([]);
  const [selectedIncome, setSelectedIncome] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState([]);
  const [selectedPayment, setSelectedPayment] = useState([]);
  const [willCancel, setWillCancel] = useState(null); // null, 0, or 1

  const fetchCustomers = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await apiService.getCustomers(page, limit, {
        searchId,
        willCancel,
        riskCategories: selectedRisk,
        incomeLevels: selectedIncome,
        deviceTypes: selectedDevice,
        paymentModes: selectedPayment
      });
      setCustomers(data.results || []);
      setTotal(data.total || 0);
    } catch (err) {
      if (err.status === 401) {
        if (onLogout) {
          onLogout({ silent: true });
        } else {
          localStorage.removeItem('access_token');
          onViewChange('login');
        }
      } else {
        setError(err.message || 'Error fetching customer list.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, [page, searchId, selectedRisk, selectedIncome, selectedDevice, selectedPayment, willCancel]);

  const handleFilterToggle = (list, setList, value) => {
    setPage(1);
    if (list.includes(value)) {
      setList(list.filter(item => item !== value));
    } else {
      setList([...list, value]);
    }
  };

  const handleResetFilters = () => {
    setSearchId('');
    setSelectedRisk([]);
    setSelectedIncome([]);
    setSelectedDevice([]);
    setSelectedPayment([]);
    setWillCancel(null);
    setPage(1);
  };

  const totalPages = Math.ceil(total / limit) || 1;

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div>
          <p style={styles.eyebrow}>Customer Intelligence Registry</p>
          <h1 style={styles.title}>Customer Directory</h1>
          <p style={styles.subtitle}>Browse and search through all registered customer profiles. Analyze churn probabilities and filter exposure dynamically.</p>
        </div>
        <div style={styles.headerCard}>
          <span style={styles.headerCardLabel}>matched records</span>
          <strong style={styles.headerCardValue}>{total.toLocaleString()}</strong>
        </div>
      </header>

      <div style={styles.mainLayout}>
        {/* Left Side: Filter Sidebar Panel */}
        <aside style={styles.sidebar}>
          <div style={styles.sidebarHeader}>
            <h3 style={styles.sidebarTitle}>Filters</h3>
            <button onClick={handleResetFilters} style={styles.resetButton}>Reset</button>
          </div>

          <div style={styles.filterSection}>
            <label style={styles.filterLabel}>Customer ID Search</label>
            <input
              type="text"
              placeholder="e.g., C10239"
              value={searchId}
              onChange={(e) => { setSearchId(e.target.value); setPage(1); }}
              style={styles.searchInput}
            />
          </div>

          <div style={styles.filterSection}>
            <label style={styles.filterLabel}>Churn Risk Category</label>
            {['Low', 'Medium', 'High'].map(risk => (
              <label key={risk} style={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={selectedRisk.includes(risk)}
                  onChange={() => handleFilterToggle(selectedRisk, setSelectedRisk, risk)}
                  style={styles.checkbox}
                />
                {risk}
              </label>
            ))}
          </div>

          <div style={styles.filterSection}>
            <label style={styles.filterLabel}>Income Level</label>
            {['Low', 'Medium', 'High'].map(income => (
              <label key={income} style={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={selectedIncome.includes(income)}
                  onChange={() => handleFilterToggle(selectedIncome, setSelectedIncome, income)}
                  style={styles.checkbox}
                />
                {income}
              </label>
            ))}
          </div>

          <div style={styles.filterSection}>
            <label style={styles.filterLabel}>Device Type</label>
            {['Android', 'iOS', 'Web', 'Mobile', 'Tablet', 'Desktop', 'Smart TV'].map(device => (
              <label key={device} style={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={selectedDevice.includes(device)}
                  onChange={() => handleFilterToggle(selectedDevice, setSelectedDevice, device)}
                  style={styles.checkbox}
                />
                {device}
              </label>
            ))}
          </div>

          <div style={styles.filterSection}>
            <label style={styles.filterLabel}>Payment Mode</label>
            {['Credit Card', 'Debit Card', 'Net Banking', 'UPI', 'Wallet', 'Digital Wallet'].map(mode => (
              <label key={mode} style={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={selectedPayment.includes(mode)}
                  onChange={() => handleFilterToggle(selectedPayment, setSelectedPayment, mode)}
                  style={styles.checkbox}
                />
                {mode}
              </label>
            ))}
          </div>

          <div style={styles.filterSection}>
            <label style={styles.filterLabel}>Churn Prediction</label>
            <div style={styles.radioGroup}>
              <label style={styles.radioLabel}>
                <input
                  type="radio"
                  name="willCancel"
                  checked={willCancel === null}
                  onChange={() => { setWillCancel(null); setPage(1); }}
                  style={styles.radio}
                />
                All
              </label>
              <label style={styles.radioLabel}>
                <input
                  type="radio"
                  name="willCancel"
                  checked={willCancel === 1}
                  onChange={() => { setWillCancel(1); setPage(1); }}
                  style={styles.radio}
                />
                Predicted Churn
              </label>
              <label style={styles.radioLabel}>
                <input
                  type="radio"
                  name="willCancel"
                  checked={willCancel === 0}
                  onChange={() => { setWillCancel(0); setPage(1); }}
                  style={styles.radio}
                />
                Predicted Retain
              </label>
            </div>
          </div>
        </aside>

        {/* Right Side: Data Grid View */}
        <main style={styles.contentArea}>
          <div style={styles.card}>
            {error && <div style={styles.errorBanner}>{error}</div>}

            {loading ? (
              <div style={styles.loader}>Querying database records…</div>
            ) : customers.length === 0 ? (
              <div style={styles.noResults}>No matching customer records found in the database.</div>
            ) : (
              <div style={styles.tableWrap}>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>Customer ID</th>
                      <th style={styles.th}>Age</th>
                      <th style={styles.th}>Income</th>
                      <th style={styles.th}>Spend</th>
                      <th style={styles.th}>Tenure</th>
                      <th style={styles.th}>Satisfaction</th>
                      <th style={styles.th}>Churn Risk</th>
                      <th style={styles.th}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {customers.map((row) => (
                      <tr key={row.customer_id} style={styles.tr}>
                        <td style={styles.tdId}>{row.customer_id}</td>
                        <td style={styles.td}>{row.age} yrs</td>
                        <td style={styles.td}>{row.income_level}</td>
                        <td style={styles.td}>${row.monthly_total_spend.toFixed(2)}</td>
                        <td style={styles.td}>{row.tenure_months} months</td>
                        <td style={styles.td}>{row.satisfaction_score}/10</td>
                        <td style={styles.td}>
                          <span style={styles.riskBadge(row.risk_category)}>
                            {row.risk_category} ({row.churn_probability.toFixed(1)}%)
                          </span>
                        </td>
                        <td style={styles.td}>
                          <button
                            onClick={() => {
                              onSelectCustomer(row.customer_id);
                              onViewChange('profile');
                            }}
                            style={styles.actionButton}
                          >
                            View Profile
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination Controls */}
            {!loading && total > 0 && (
              <div style={styles.paginationRow}>
                <span style={styles.pageInfo}>
                  Page {page} of {totalPages}
                </span>
                <div style={styles.paginationButtons}>
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    style={page === 1 ? styles.paginationBtnDisabled : styles.paginationBtn}
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    style={page === totalPages ? styles.paginationBtnDisabled : styles.paginationBtn}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

const styles = {
  page: { minHeight: '100vh', background: '#07111f', color: '#f7f8fc', padding: '24px', fontFamily: 'Inter, Arial, sans-serif' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' },
  eyebrow: { textTransform: 'uppercase', letterSpacing: '0.18em', color: '#7dd3fc', fontSize: '0.75rem', margin: 0 },
  title: { margin: '4px 0 8px', fontSize: '2rem' },
  subtitle: { margin: 0, color: '#94a3b8', maxWidth: '620px', lineHeight: 1.7 },
  headerCard: { background: 'rgba(17,24,39,0.85)', border: '1px solid rgba(255,255,255,0.08)', padding: '16px 20px', borderRadius: '16px', minWidth: '200px', display: 'flex', flexDirection: 'column', gap: '4px', textAlign: 'right' },
  headerCardLabel: { color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.14em', fontSize: '0.7rem' },
  headerCardValue: { fontSize: '2rem', lineHeight: 1.05, margin: 0 },
  mainLayout: { display: 'grid', gridTemplateColumns: '280px 1fr', gap: '24px', alignItems: 'start' },
  sidebar: { background: 'rgba(17,24,39,0.85)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '18px', position: 'sticky', top: '24px' },
  sidebarHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '10px' },
  sidebarTitle: { margin: 0, fontSize: '1.1rem', color: '#f8fafc' },
  resetButton: { background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600 },
  filterSection: { display: 'flex', flexDirection: 'column', gap: '8px' },
  filterLabel: { fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94a3b8', fontWeight: 600 },
  searchInput: { background: '#0b1626', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '10px', color: '#f7f8fc', outline: 'none', fontSize: '0.9rem' },
  checkboxLabel: { display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9rem', color: '#cbd5e1', cursor: 'pointer' },
  checkbox: { width: '16px', height: '16px', cursor: 'pointer', accentColor: '#38bdf8' },
  radioGroup: { display: 'flex', flexDirection: 'column', gap: '8px' },
  radioLabel: { display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9rem', color: '#cbd5e1', cursor: 'pointer' },
  radio: { width: '16px', height: '16px', cursor: 'pointer', accentColor: '#38bdf8' },
  contentArea: { display: 'flex', flexDirection: 'column', gap: '20px' },
  card: { background: 'rgba(17,24,39,0.8)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '24px', boxShadow: '0 12px 34px rgba(0,0,0,0.25)' },
  loader: { padding: '40px 0', color: '#38bdf8', fontStyle: 'italic', display: 'flex', justifyContent: 'center' },
  noResults: { padding: '40px 0', textAlign: 'center', color: '#94a3b8' },
  errorBanner: { background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', padding: '12px', borderRadius: '8px', color: '#fca5a5', marginBottom: '16px', fontSize: '0.9rem' },
  tableWrap: { overflowX: 'auto', width: '100%' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', padding: '12px 16px', color: '#94a3b8', borderBottom: '1px solid rgba(255,255,255,0.08)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' },
  tr: { transition: 'background-color 0.2s' },
  tdId: { padding: '14px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)', fontFamily: 'monospace', fontWeight: 600, color: '#38bdf8' },
  td: { padding: '14px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)', fontSize: '0.9rem', color: '#e2e8f0' },
  riskBadge: (category) => {
    const isHigh = category === 'High' || category === 'CRITICAL';
    const isMedium = category === 'Medium';
    const bg = isHigh ? 'rgba(239,68,68,0.1)' : isMedium ? 'rgba(245,158,11,0.1)' : 'rgba(16,185,129,0.1)';
    const text = isHigh ? '#fca5a5' : isMedium ? '#fde047' : '#a7f3d0';
    const border = isHigh ? 'rgba(239,68,68,0.2)' : isMedium ? 'rgba(245,158,11,0.2)' : 'rgba(16,185,129,0.2)';
    return {
      padding: '4px 8px',
      borderRadius: '6px',
      fontSize: '0.8rem',
      fontWeight: 600,
      backgroundColor: bg,
      color: text,
      border: `1px solid ${border}`
    };
  },
  actionButton: { background: 'rgba(56,189,248,0.1)', color: '#38bdf8', border: '1px solid rgba(56,189,248,0.2)', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600, transition: 'all 0.2s' },
  paginationRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '16px' },
  pageInfo: { color: '#94a3b8', fontSize: '0.9rem' },
  paginationButtons: { display: 'flex', gap: '8px' },
  paginationBtn: { background: 'rgba(255,255,255,0.05)', color: '#f7f8fc', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '8px 16px', fontSize: '0.85rem', cursor: 'pointer', fontWeight: 500 },
  paginationBtnDisabled: { background: 'rgba(255,255,255,0.02)', color: '#475569', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px', padding: '8px 16px', fontSize: '0.85rem', cursor: 'not-allowed' }
};
