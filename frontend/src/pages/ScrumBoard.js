import React from 'react';

const columns = [
  {
    title: 'To Do',
    items: ['Review churn threshold logic', 'Add retention playbook copy', 'Validate CSV edge cases']
  },
  {
    title: 'In Progress',
    items: ['Alert notifications', 'Dashboard QA pass']
  },
  {
    title: 'Done',
    items: ['Authentication flow', 'Model performance view', 'Customer profile predictions']
  }
];

export default function ScrumBoard() {
  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div>
          <p style={styles.eyebrow}>Delivery Board</p>
          <h1 style={styles.title}>Scrum board</h1>
          <p style={styles.subtitle}>Track product work across the churn prediction dashboard.</p>
        </div>
      </header>

      <section style={styles.board}>
        {columns.map((column) => (
          <div key={column.title} style={styles.column}>
            <div style={styles.columnHeader}>
              <h2 style={styles.columnTitle}>{column.title}</h2>
              <span style={styles.count}>{column.items.length}</span>
            </div>
            <div style={styles.itemList}>
              {column.items.map((item) => (
                <article key={item} style={styles.item}>
                  {item}
                </article>
              ))}
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}

const styles = {
  page: {
    minHeight: '100%',
    padding: '32px',
    background: '#07111f',
    color: '#e2e8f0'
  },
  header: {
    marginBottom: '24px'
  },
  eyebrow: {
    margin: '0 0 8px',
    color: '#38bdf8',
    fontSize: '0.78rem',
    fontWeight: 700,
    letterSpacing: '0.08em',
    textTransform: 'uppercase'
  },
  title: {
    margin: 0,
    fontFamily: 'Outfit, sans-serif',
    fontSize: '2rem',
    color: '#f8fafc'
  },
  subtitle: {
    margin: '8px 0 0',
    color: '#94a3b8',
    maxWidth: '620px'
  },
  board: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: '16px'
  },
  column: {
    background: 'rgba(15, 23, 42, 0.78)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '8px',
    padding: '16px',
    minHeight: '280px'
  },
  columnHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '14px'
  },
  columnTitle: {
    margin: 0,
    fontSize: '1rem',
    color: '#f8fafc'
  },
  count: {
    minWidth: '28px',
    height: '28px',
    borderRadius: '50%',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(99, 102, 241, 0.16)',
    color: '#c4b5fd',
    fontSize: '0.85rem',
    fontWeight: 700
  },
  itemList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px'
  },
  item: {
    background: 'rgba(2, 6, 23, 0.46)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '8px',
    padding: '12px',
    color: '#cbd5e1',
    lineHeight: 1.45
  }
};
