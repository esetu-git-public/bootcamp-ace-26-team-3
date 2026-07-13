import React, { useState, useEffect } from 'react';

const INITIAL_TASKS = [
  { id: 'US-101', title: 'Customer Churn Data Pipeline', type: 'story', sp: 5, status: 'Done', sprint: 'Sprint 1', desc: 'Build a robust preprocessing pipeline to clean, scale, and encode customer data.' },
  { id: 'US-102', title: 'Predictive Feature Engineering', type: 'story', sp: 5, status: 'Done', sprint: 'Sprint 2', desc: 'Engineer 5 interaction features (e.g. Spend_Per_Subscription, Engagement_Score) to boost predictive power.' },
  { id: 'US-201', title: 'CatBoost Model Training', type: 'story', sp: 8, status: 'Done', sprint: 'Sprint 2', desc: 'Select and tune CatBoost classifier model to maximize F1-score (target > 0.80) and AUC.' },
  { id: 'US-202', title: 'Advanced XAI with SHAP', type: 'story', sp: 8, status: 'Done', sprint: 'Sprint 3', desc: 'Create tree SHAP explainability calculations and visualizer for local/global predictions.' },
  { id: 'US-203', title: 'Confidence Intervals Calibration', type: 'story', sp: 5, status: 'Done', sprint: 'Sprint 3', desc: 'Standardize outputs to 0-100% and compute 95% binomial confidence bounds around prediction margins.' },
  { id: 'US-301', title: 'JWT Security & Auth Router', type: 'story', sp: 5, status: 'Done', sprint: 'Sprint 3', desc: 'Secure backend routes using FastAPI Security and user authentication with JWT bearer tokens.' },
  { id: 'US-302', title: 'Core FastAPI REST Endpoints', type: 'story', sp: 8, status: 'Done', sprint: 'Sprint 3', desc: 'Deliver paginated directory, profile audit, dashboard metrics, and prediction routes.' },
  { id: 'US-401', title: 'Executive React Dashboard', type: 'story', sp: 8, status: 'Done', sprint: 'Sprint 3', desc: 'Build visual charts dashboard featuring KPI metrics, segment distributions, and risk queue.' },
  { id: 'US-402', title: 'Customer Directory view', type: 'story', sp: 5, status: 'Done', sprint: 'Sprint 3', desc: 'Render search filters dashboard matching pagination, ID lookup, and column sorting.' },
  { id: 'US-403', title: 'Profile Explorer & XAI Visuals', type: 'story', sp: 8, status: 'Done', sprint: 'Sprint 3', desc: 'Provide deep-dive profiles showing circular risk gauges, SHAP impact bars, and audit timeline.' },
  { id: 'US-404', title: 'Frontend Service Abstract', type: 'story', sp: 5, status: 'Done', sprint: 'Sprint 3', desc: 'Refactor fetch routines into dedicated services (api.js, mlModel.js) to reduce component logic.' },
  { id: 'US-501', title: 'Bulk Prediction Studio', type: 'story', sp: 8, status: 'Done', sprint: 'Sprint 3', desc: 'Provide asynchronous CSV uploader, execution status pollers, results preview, and file downloads.' },
  { id: 'US-502', title: 'Export Reporting Service', type: 'story', sp: 5, status: 'Done', sprint: 'Sprint 3', desc: 'Implement report exporters formatting PDF summaries, Excel sheets, and filtered CSV downloads.' },
  { id: 'US-503', title: 'Seed & Recalculation Prediction Alignment', type: 'story', sp: 3, status: 'Done', sprint: 'Sprint 4', desc: 'Ensure database seed predictions and dynamic recalculate buttons use identical model pipelines to prevent values shifting.' },
  
  { id: 'BUG-001', title: 'Async Test Suite Failure', type: 'bug', sp: 3, status: 'Done', sprint: 'Sprint 4', desc: 'Async bulk prediction tests fail because pytest-asyncio is not installed or configured.', priority: 'High' },
  { id: 'BUG-002', title: 'FastAPI Query Deprecation Warning', type: 'bug', sp: 1, status: 'Done', sprint: 'Sprint 4', desc: 'Query parameter regex is deprecated in reports.py, replace with pattern parameter.', priority: 'Low' },
  { id: 'BUG-003', title: 'Pydantic Field example Warning', type: 'bug', sp: 1, status: 'Done', sprint: 'Sprint 4', desc: 'Attribute example is deprecated in common.py schemas, replace with json_schema_extra.', priority: 'Low' },
  { id: 'BUG-004', title: 'ML Model Pickle Version Mismatch', type: 'bug', sp: 3, status: 'Backlog', sprint: 'Backlog', desc: 'SimpleImputer / StandardScaler pickled with newer sklearn version 1.8.0 throws unpickling warnings in 1.6.1.', priority: 'Medium' },
  { id: 'BUG-005', title: 'datetime.utcnow() Deprecations', type: 'bug', sp: 1, status: 'Backlog', sprint: 'Backlog', desc: 'Code relies on deprecated timezone-naive datetime.utcnow(), use timezone-aware datetime.now(datetime.UTC).', priority: 'Low' },
  { id: 'BUG-006', title: 'Webpack Dev Server Warnings', type: 'bug', sp: 2, status: 'Backlog', sprint: 'Backlog', desc: 'fs.F_OK and setupMiddlewares deprecation warnings on npm start, update react-scripts dependencies.', priority: 'Low' }

];

const COLUMNS = [
  { id: 'Backlog', title: 'Product Backlog', desc: 'Ready for grooming / Unplanned', color: '#94a3b8' },
  { id: 'Todo', title: 'Sprint Backlog', desc: 'Planned for immediate action', color: '#f59e0b' },
  { id: 'InProgress', title: 'In Progress', desc: 'Active development / testing', color: '#38bdf8' },
  { id: 'Done', title: 'Done', desc: 'Fully verified & production ready', color: '#10b981' }
];

const SPRINTS = [
  { id: 'all', title: 'All Sprints', desc: 'Complete project backlog' },
  { id: 'Sprint 1', title: 'Sprint 1', desc: 'Data Preprocessing & Setup' },
  { id: 'Sprint 2', title: 'Sprint 2', desc: 'ML Model & Hyperparameter Tuning' },
  { id: 'Sprint 3', title: 'Sprint 3', desc: 'Backend Endpoints & UI Interface' },
  { id: 'Sprint 4', title: 'Sprint 4', desc: 'Bug-fix & Deprecations Sprint' },
  { id: 'Backlog', title: 'Unscheduled', desc: 'Future backlog features & bugs' }
];

export default function ScrumBoard({ onViewChange }) {
  const [tasks, setTasks] = useState(() => {
    const saved = localStorage.getItem('scrum_tasks_sprints');
    return saved ? JSON.parse(saved) : INITIAL_TASKS;
  });

  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all'); // all, story, bug
  const [selectedSprint, setSelectedSprint] = useState('all'); // all, Sprint 1, 2, 3, 4, Backlog
  const [selectedTask, setSelectedTask] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);

  // Form State
  const [newTitle, setNewTitle] = useState('');
  const [newType, setNewType] = useState('story');
  const [newSp, setNewSp] = useState(3);
  const [newDesc, setNewDesc] = useState('');
  const [newPriority, setNewPriority] = useState('Medium');
  const [newStatus, setNewStatus] = useState('Backlog');
  const [newSprint, setNewSprint] = useState('Sprint 4');

  useEffect(() => {
    localStorage.setItem('scrum_tasks_sprints', JSON.stringify(tasks));
  }, [tasks]);

  const moveTask = (taskId, newStatus) => {
    setTasks(prev => prev.map(task => 
      task.id === taskId ? { ...task, status: newStatus } : task
    ));
    if (selectedTask && selectedTask.id === taskId) {
      setSelectedTask(prev => ({ ...prev, status: newStatus }));
    }
  };

  const updateTaskSprint = (taskId, sprintValue) => {
    setTasks(prev => prev.map(task => 
      task.id === taskId ? { ...task, sprint: sprintValue } : task
    ));
    if (selectedTask && selectedTask.id === taskId) {
      setSelectedTask(prev => ({ ...prev, sprint: sprintValue }));
    }
  };

  const handleDragStart = (e, taskId) => {
    e.dataTransfer.setData('text/plain', taskId);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e, columnId) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('text/plain');
    if (taskId) {
      moveTask(taskId, columnId);
    }
  };

  const handleAddTask = (e) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    const count = tasks.filter(t => t.type === newType).length + 1;
    const prefix = newType === 'story' ? 'US' : 'BUG';
    const id = `${prefix}-${String(count).padStart(3, '0')}`;

    const newTask = {
      id,
      title: newTitle,
      type: newType,
      sp: Number(newSp) || 0,
      status: newStatus,
      sprint: newSprint,
      desc: newDesc,
      priority: newType === 'bug' ? newPriority : undefined
    };

    setTasks(prev => [...prev, newTask]);
    setShowAddModal(false);
    
    // Clear form
    setNewTitle('');
    setNewDesc('');
    setNewSp(3);
    setNewType('story');
    setNewPriority('Medium');
    setNewStatus('Backlog');
    setNewSprint('Sprint 4');
  };

  const handleDeleteTask = (taskId) => {
    if (window.confirm(`Are you sure you want to delete ${taskId}?`)) {
      setTasks(prev => prev.filter(t => t.id !== taskId));
      setSelectedTask(null);
    }
  };

  const resetBoard = () => {
    if (window.confirm('Are you sure you want to reset the board to the default state? All customized tasks and sprint settings will be lost.')) {
      setTasks(INITIAL_TASKS);
    }
  };

  // Calculations for current selected filter context
  const activeSprintTasks = tasks.filter(t => selectedSprint === 'all' || t.sprint === selectedSprint);
  const totalStoryPoints = activeSprintTasks.reduce((sum, t) => sum + (t.sp || 0), 0);
  const completedStoryPoints = activeSprintTasks.filter(t => t.status === 'Done').reduce((sum, t) => sum + (t.sp || 0), 0);
  const completionRate = totalStoryPoints > 0 ? (completedStoryPoints / totalStoryPoints) * 100 : 0;
  
  const activeBugsCount = activeSprintTasks.filter(t => t.type === 'bug' && t.status !== 'Done').length;
  const completedStoriesCount = activeSprintTasks.filter(t => t.type === 'story' && t.status === 'Done').length;
  const totalStoriesCount = activeSprintTasks.filter(t => t.type === 'story').length;

  const filteredTasks = tasks.filter(t => {
    const matchesSearch = t.title.toLowerCase().includes(searchTerm.toLowerCase()) || t.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = filterType === 'all' || t.type === filterType;
    const matchesSprint = selectedSprint === 'all' || t.sprint === selectedSprint;
    return matchesSearch && matchesType && matchesSprint;
  });

  return (
    <div style={styles.page}>
      {/* Header */}
      <header style={styles.header}>
        <div>
          <p style={styles.eyebrow}>Workspace Agile Tracking</p>
          <h1 style={styles.title}>Scrum Story Board</h1>
          <p style={styles.subtitle}>
            A live, interactive view of features, tasks, and bugs. Group tasks by Sprints using the tabs below. Drag-and-drop cards to manage workflow.
          </p>
        </div>
        <div style={styles.headerActions}>
          <button onClick={() => setShowAddModal(true)} style={styles.addBtn}>
            + Create Ticket
          </button>
          <button onClick={resetBoard} style={styles.resetBtn}>
            Reset Board
          </button>
          <button onClick={() => onViewChange('dashboard')} style={styles.backBtn}>
            Dashboard
          </button>
        </div>
      </header>

      {/* Sprints Tab Selector */}
      <section style={styles.sprintsSection}>
        <div style={styles.sprintTabs}>
          {SPRINTS.map(sprint => (
            <button
              key={sprint.id}
              onClick={() => setSelectedSprint(sprint.id)}
              style={selectedSprint === sprint.id ? styles.sprintTabActive : styles.sprintTab}
              title={sprint.desc}
            >
              <div style={styles.sprintTabTitle}>{sprint.title}</div>
              <div style={styles.sprintTabDesc}>
                {tasks.filter(t => t.sprint === sprint.id || (sprint.id === 'all')).length} Tasks
              </div>
            </button>
          ))}
        </div>
      </section>

      {/* Metrics Panel */}
      <section style={styles.metricsPanel}>
        <div style={styles.metricItem}>
          <span style={styles.metricLabel}>
            {selectedSprint === 'all' ? 'Overall Backlog Progress' : `${selectedSprint} Progress`}
          </span>
          <div style={styles.progressContainer}>
            <strong style={styles.metricValue}>
              {completedStoryPoints} <span style={styles.metricSub}>/ {totalStoryPoints} SP</span>
            </strong>
            <div style={styles.progressBarTrack}>
              <div style={{ ...styles.progressBarFill, width: `${completionRate}%` }} />
            </div>
            <span style={styles.progressPercent}>{completionRate.toFixed(1)}% Completed</span>
          </div>
        </div>
        <div style={styles.metricMiniGrid}>
          <div style={styles.miniCard}>
            <span style={styles.miniLabel}>User Stories Done</span>
            <strong style={styles.miniValue}>{completedStoriesCount} <span style={styles.miniSub}>/ {totalStoriesCount}</span></strong>
          </div>
          <div style={styles.miniCard}>
            <span style={styles.miniLabel}>Active Bugs (Unresolved)</span>
            <strong style={{ ...styles.miniValue, color: activeBugsCount > 0 ? '#ef4444' : '#10b981' }}>{activeBugsCount}</strong>
          </div>
        </div>
      </section>

      {/* Search & Filters */}
      <section style={styles.filtersBar}>
        <input
          type="text"
          placeholder="Search tasks by title or ticket ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={styles.searchInput}
        />
        <div style={styles.filterGroup}>
          <span style={styles.filterLabel}>Type:</span>
          <button 
            onClick={() => setFilterType('all')} 
            style={filterType === 'all' ? styles.filterBtnActive : styles.filterBtn}
          >
            All
          </button>
          <button 
            onClick={() => setFilterType('story')} 
            style={filterType === 'story' ? styles.filterBtnActive : styles.filterBtn}
          >
            Stories
          </button>
          <button 
            onClick={() => setFilterType('bug')} 
            style={filterType === 'bug' ? styles.filterBtnActive : styles.filterBtn}
          >
            Bugs
          </button>
        </div>
      </section>

      {/* Kanban Board Grid */}
      <section style={styles.boardGrid}>
        {COLUMNS.map(col => {
          const colTasks = filteredTasks.filter(t => t.status === col.id);
          const colSp = colTasks.reduce((sum, t) => sum + (t.sp || 0), 0);

          return (
            <div 
              key={col.id} 
              style={styles.column}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, col.id)}
            >
              <div style={{ ...styles.columnHeader, borderTop: `3px solid ${col.color}` }}>
                <div>
                  <h3 style={styles.columnTitle}>{col.title}</h3>
                  <span style={styles.columnDesc}>{col.desc}</span>
                </div>
                <div style={styles.columnBadges}>
                  <span style={styles.countBadge}>{colTasks.length}</span>
                  {colSp > 0 && <span style={styles.spBadge}>{colSp} SP</span>}
                </div>
              </div>

              <div style={styles.columnBody}>
                {colTasks.length === 0 ? (
                  <div style={styles.emptyColumn}>Drop cards here</div>
                ) : (
                  colTasks.map(task => (
                    <div
                      key={task.id}
                      draggable
                      onDragStart={(e) => handleDragStart(e, task.id)}
                      onClick={() => setSelectedTask(task)}
                      style={{
                        ...styles.card,
                        borderLeft: `4px solid ${task.type === 'bug' ? '#ef4444' : '#6366f1'}`
                      }}
                    >
                      <div style={styles.cardHeader}>
                        <span style={{ 
                          ...styles.cardId, 
                          color: task.type === 'bug' ? '#fca5a5' : '#818cf8',
                          background: task.type === 'bug' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(99, 102, 241, 0.15)'
                        }}>
                          {task.id}
                        </span>
                        
                        <span style={{ ...styles.cardSprintBadge, color: task.sprint === 'Backlog' ? '#94a3b8' : '#22d3ee' }}>
                          {task.sprint === 'Backlog' ? 'Backlog' : task.sprint}
                        </span>
                      </div>
                      
                      <h4 style={styles.cardTitle}>{task.title}</h4>
                      <p style={styles.cardDesc}>{task.desc}</p>
                      
                      {/* Priority Tag for Bugs */}
                      {task.type === 'bug' && task.priority && (
                        <div style={{ marginTop: '2px' }}>
                          <span style={{ 
                            ...styles.priorityTag,
                            backgroundColor: task.priority === 'High' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                            color: task.priority === 'High' ? '#ef4444' : '#f59e0b',
                            border: `1px solid ${task.priority === 'High' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`
                          }}>
                            {task.priority} Priority
                          </span>
                        </div>
                      )}

                      {/* Interactive click indicator and micro-actions */}
                      <div style={styles.cardFooter}>
                        <div style={styles.spLabel}>
                          {task.sp > 0 ? `${task.sp} SP` : '0 SP'}
                        </div>
                        <div style={styles.arrowControls}>
                          {col.id !== 'Backlog' && (
                            <button 
                              onClick={(e) => { e.stopPropagation(); moveTask(task.id, COLUMNS[COLUMNS.findIndex(c => c.id === col.id) - 1].id); }} 
                              style={styles.arrowBtn}
                              title="Move Left"
                            >
                              ◀
                            </button>
                          )}
                          {col.id !== 'Done' && (
                            <button 
                              onClick={(e) => { e.stopPropagation(); moveTask(task.id, COLUMNS[COLUMNS.findIndex(c => c.id === col.id) + 1].id); }} 
                              style={styles.arrowBtn}
                              title="Move Right"
                            >
                              ▶
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </section>

      {/* Task Details Modal */}
      {selectedTask && (
        <div style={styles.modalOverlay} onClick={() => setSelectedTask(null)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <header style={styles.modalHeader}>
              <div>
                <span style={{ 
                  ...styles.modalId, 
                  color: selectedTask.type === 'bug' ? '#ef4444' : '#818cf8',
                  background: selectedTask.type === 'bug' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(99, 102, 241, 0.15)'
                }}>
                  {selectedTask.id} ({selectedTask.type.toUpperCase()})
                </span>
                <h2 style={styles.modalTitle}>{selectedTask.title}</h2>
              </div>
              <button onClick={() => setSelectedTask(null)} style={styles.modalCloseBtn}>✕</button>
            </header>
            
            <div style={styles.modalBody}>
              <div style={styles.modalMain}>
                <h4 style={styles.modalSectionHeading}>Description</h4>
                <p style={styles.modalDesc}>{selectedTask.desc || 'No description provided.'}</p>
              </div>
              
              <div style={styles.modalSidebar}>
                <h4 style={styles.modalSectionHeading}>Agile Planning</h4>
                
                <div style={styles.modalMetaRow}>
                  <span>Story Points:</span>
                  <strong>{selectedTask.sp} SP</strong>
                </div>

                <div style={styles.modalMetaRowSelect}>
                  <span>Sprint:</span>
                  <select 
                    value={selectedTask.sprint} 
                    onChange={(e) => updateTaskSprint(selectedTask.id, e.target.value)}
                    style={styles.modalSelect}
                  >
                    {SPRINTS.filter(s => s.id !== 'all').map(s => (
                      <option key={s.id} value={s.id}>{s.title}</option>
                    ))}
                  </select>
                </div>

                {selectedTask.type === 'bug' && selectedTask.priority && (
                  <div style={styles.modalMetaRow}>
                    <span>Priority:</span>
                    <strong style={{ color: selectedTask.priority === 'High' ? '#ef4444' : '#f59e0b' }}>
                      {selectedTask.priority}
                    </strong>
                  </div>
                )}
                <div style={styles.modalMetaRow}>
                  <span>Current Column:</span>
                  <strong>{COLUMNS.find(c => c.id === selectedTask.status)?.title}</strong>
                </div>

                <h4 style={styles.modalSectionHeading}>Status Transition</h4>
                <div style={styles.statusButtonsGrid}>
                  {COLUMNS.map(col => (
                    <button
                      key={col.id}
                      onClick={() => moveTask(selectedTask.id, col.id)}
                      style={selectedTask.status === col.id ? styles.activeStatusBtn : styles.statusBtn}
                    >
                      {col.title}
                    </button>
                  ))}
                </div>

                <div style={styles.deleteZone}>
                  <button onClick={() => handleDeleteTask(selectedTask.id)} style={styles.deleteBtn}>
                    Delete Ticket
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Task Modal */}
      {showAddModal && (
        <div style={styles.modalOverlay} onClick={() => setShowAddModal(false)}>
          <form onSubmit={handleAddTask} style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <header style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>Create New Scrum Ticket</h2>
              <button type="button" onClick={() => setShowAddModal(false)} style={styles.modalCloseBtn}>✕</button>
            </header>
            
            <div style={styles.modalBody}>
              <div style={styles.formGrid}>
                <div style={styles.formGroupFull}>
                  <label style={styles.formLabel}>Title *</label>
                  <input
                    type="text"
                    required
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="e.g. Implement dashboard charts caching"
                    style={styles.formInput}
                  />
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Ticket Type</label>
                  <select
                    value={newType}
                    onChange={(e) => setNewType(e.target.value)}
                    style={styles.formSelect}
                  >
                    <option value="story">User Story</option>
                    <option value="bug">Bug</option>
                  </select>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Story Points</label>
                  <input
                    type="number"
                    min="0"
                    value={newSp}
                    onChange={(e) => setNewSp(e.target.value)}
                    style={styles.formInput}
                  />
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Assign Sprint</label>
                  <select
                    value={newSprint}
                    onChange={(e) => setNewSprint(e.target.value)}
                    style={styles.formSelect}
                  >
                    {SPRINTS.filter(s => s.id !== 'all').map(s => (
                      <option key={s.id} value={s.id}>{s.title}</option>
                    ))}
                  </select>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Initial Column</label>
                  <select
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value)}
                    style={styles.formSelect}
                  >
                    {COLUMNS.map(c => (
                      <option key={c.id} value={c.id}>{c.title}</option>
                    ))}
                  </select>
                </div>

                {newType === 'bug' && (
                  <div style={styles.formGroup}>
                    <label style={styles.formLabel}>Bug Priority</label>
                    <select
                      value={newPriority}
                      onChange={(e) => setNewPriority(e.target.value)}
                      style={styles.formSelect}
                    >
                      <option value="Low">Low</option>
                      <option value="Medium">Medium</option>
                      <option value="High">High</option>
                    </select>
                  </div>
                )}

                <div style={styles.formGroupFull}>
                  <label style={styles.formLabel}>Description</label>
                  <textarea
                    rows="4"
                    value={newDesc}
                    onChange={(e) => setNewDesc(e.target.value)}
                    placeholder="Provide details, acceptance criteria, or reproduction steps..."
                    style={styles.formTextarea}
                  />
                </div>
              </div>
            </div>

            <footer style={styles.modalFooter}>
              <button type="button" onClick={() => setShowAddModal(false)} style={styles.formCancelBtn}>
                Cancel
              </button>
              <button type="submit" style={styles.formSubmitBtn}>
                Create Ticket
              </button>
            </footer>
          </form>
        </div>
      )}
    </div>
  );
}

const styles = {
  page: { minHeight: 'calc(100vh - 70px)', background: '#07111f', color: '#f7f8fc', padding: '24px', fontFamily: 'Inter, Arial, sans-serif', display: 'flex', flexDirection: 'column', gap: '20px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' },
  eyebrow: { textTransform: 'uppercase', letterSpacing: '0.18em', color: '#7dd3fc', fontSize: '0.75rem', margin: 0 },
  title: { margin: '4px 0 8px', fontSize: '2rem', fontWeight: 700 },
  subtitle: { margin: 0, color: '#94a3b8', maxWidth: '750px', lineHeight: 1.6 },
  headerActions: { display: 'flex', gap: '10px' },
  addBtn: { background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)', border: 'none', borderRadius: '12px', color: '#ffffff', padding: '10px 20px', fontSize: '0.9rem', fontWeight: 600, cursor: 'pointer', boxShadow: '0 4px 14px rgba(99, 102, 241, 0.4)' },
  resetBtn: { background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '12px', color: '#cbd5e1', padding: '10px 20px', fontSize: '0.9rem', fontWeight: 600, cursor: 'pointer' },
  backBtn: { background: 'rgba(99, 102, 241, 0.12)', border: '1px solid rgba(99, 102, 241, 0.3)', borderRadius: '12px', color: '#818cf8', padding: '10px 20px', fontSize: '0.9rem', fontWeight: 600, cursor: 'pointer' },
  
  // Sprint Section Tabs
  sprintsSection: { display: 'flex', overflowX: 'auto', paddingBottom: '4px', borderBottom: '1px solid rgba(255, 255, 255, 0.06)' },
  sprintTabs: { display: 'flex', gap: '12px' },
  sprintTab: { background: 'rgba(15, 23, 42, 0.4)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', color: '#94a3b8', padding: '10px 20px', cursor: 'pointer', textAlign: 'left', minWidth: '150px', transition: 'all 0.2s' },
  sprintTabActive: { background: 'rgba(99, 102, 241, 0.12)', border: '1.5px solid #6366f1', borderRadius: '12px', color: '#818cf8', padding: '10px 20px', cursor: 'pointer', textAlign: 'left', minWidth: '150px', boxShadow: '0 0 12px rgba(99, 102, 241, 0.15)' },
  sprintTabTitle: { fontSize: '0.9rem', fontWeight: 700, marginBottom: '4px' },
  sprintTabDesc: { fontSize: '0.75rem', color: '#64748b' },

  // Metrics Panel
  metricsPanel: { display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px', background: 'rgba(15,23,42,0.4)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '16px', padding: '20px', flexWrap: 'wrap' },
  metricItem: { display: 'flex', flexDirection: 'column', gap: '10px' },
  metricLabel: { color: '#94a3b8', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' },
  metricValue: { fontSize: '1.8rem', color: '#ffffff', fontWeight: 700 },
  metricSub: { fontSize: '1rem', color: '#64748b', fontWeight: 400 },
  progressContainer: { display: 'flex', flexDirection: 'column', gap: '8px' },
  progressBarTrack: { height: '10px', background: 'rgba(255,255,255,0.06)', borderRadius: '999px', overflow: 'hidden' },
  progressBarFill: { height: '100%', background: 'linear-gradient(90deg, #6366f1, #10b981)', borderRadius: '999px', transition: 'width 0.5s ease-out' },
  progressPercent: { fontSize: '0.8rem', color: '#10b981', alignSelf: 'flex-end', fontWeight: 600 },
  metricMiniGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' },
  miniCard: { background: 'rgba(17,24,39,0.5)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '12px', padding: '14px', display: 'flex', flexDirection: 'column', justifyContent: 'center' },
  miniLabel: { color: '#94a3b8', fontSize: '0.75rem', marginBottom: '6px' },
  miniValue: { fontSize: '1.4rem', color: '#ffffff', fontWeight: 700 },
  miniSub: { fontSize: '0.85rem', color: '#64748b', fontWeight: 400 },

  // Filters Bar
  filtersBar: { display: 'flex', gap: '20px', alignItems: 'center', flexWrap: 'wrap' },
  searchInput: { flex: 1, minWidth: '240px', background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', color: '#ffffff', padding: '12px 18px', fontSize: '0.95rem' },
  filterGroup: { display: 'flex', gap: '8px', alignItems: 'center' },
  filterLabel: { color: '#94a3b8', fontSize: '0.85rem', marginRight: '4px' },
  filterBtn: { background: 'none', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', color: '#94a3b8', padding: '6px 14px', fontSize: '0.85rem', cursor: 'pointer', fontWeight: 500 },
  filterBtnActive: { background: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.4)', borderRadius: '8px', color: '#818cf8', padding: '6px 14px', fontSize: '0.85rem', cursor: 'pointer', fontWeight: 600 },

  // Kanban Board Layout
  boardGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', alignItems: 'start', flex: 1 },
  column: { background: 'rgba(15,23,42,0.4)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '16px', display: 'flex', flexDirection: 'column', maxHeight: '70vh', minHeight: '350px' },
  columnHeader: { padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid rgba(255,255,255,0.05)' },
  columnTitle: { margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' },
  columnDesc: { fontSize: '0.75rem', color: '#64748b', marginTop: '2px', display: 'block' },
  columnBadges: { display: 'flex', gap: '6px', alignItems: 'center' },
  countBadge: { background: 'rgba(255,255,255,0.06)', borderRadius: '6px', color: '#94a3b8', fontSize: '0.75rem', fontWeight: 700, padding: '2px 6px' },
  spBadge: { background: 'rgba(99,102,241,0.12)', borderRadius: '6px', color: '#818cf8', fontSize: '0.75rem', fontWeight: 700, padding: '2px 6px' },
  columnBody: { padding: '12px', display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', flex: 1 },
  emptyColumn: { border: '2px dashed rgba(255,255,255,0.03)', borderRadius: '12px', padding: '24px', textAlign: 'center', color: '#475569', fontSize: '0.85rem' },

  // Task Cards
  card: { background: 'rgba(17, 24, 39, 0.75)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255, 255, 255, 0.06)', borderRadius: '12px', padding: '14px', cursor: 'grab', display: 'flex', flexDirection: 'column', gap: '8px', transition: 'transform 0.15s, box-shadow 0.15s', ':hover': { transform: 'translateY(-2px)', boxShadow: '0 8px 24px rgba(0,0,0,0.3)' } },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' },
  cardId: { fontSize: '0.72rem', fontWeight: 700, padding: '2px 6px', borderRadius: '4px' },
  cardSprintBadge: { fontSize: '0.72rem', fontWeight: 600, opacity: 0.8 },
  cardTitle: { margin: 0, fontSize: '0.92rem', fontWeight: 600, color: '#f1f5f9', lineHeight: 1.4 },
  cardDesc: { margin: 0, fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' },
  priorityTag: { fontSize: '0.65rem', padding: '1px 5px', borderRadius: '4px', fontWeight: 600, display: 'inline-block' },
  cardFooter: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px', borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '8px' },
  spLabel: { fontSize: '0.75rem', color: '#cbd5e1', fontWeight: 600 },
  arrowControls: { display: 'flex', gap: '4px' },
  arrowBtn: { background: 'rgba(255,255,255,0.05)', border: 'none', borderRadius: '4px', color: '#94a3b8', cursor: 'pointer', fontSize: '0.65rem', padding: '3px 6px', ':hover': { background: 'rgba(255,255,255,0.1)', color: '#ffffff' } },

  // Modals System
  modalOverlay: { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1100, padding: '20px' },
  modalContent: { background: '#0b1329', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '20px', width: '100%', maxWidth: '700px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 50px rgba(0,0,0,0.5)' },
  modalHeader: { padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid rgba(255,255,255,0.06)' },
  modalTitle: { margin: '4px 0 0 0', fontSize: '1.3rem', fontWeight: 700, color: '#f8fafc' },
  modalId: { fontSize: '0.8rem', fontWeight: 700, padding: '3px 8px', borderRadius: '6px', display: 'inline-block' },
  modalCloseBtn: { background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '1.2rem' },
  modalBody: { padding: '20px', overflowY: 'auto', flex: 1, display: 'flex', gap: '20px', flexWrap: 'wrap' },
  modalMain: { flex: 1.4, minWidth: '280px', display: 'flex', flexDirection: 'column', gap: '16px' },
  modalSidebar: { flex: 1, minWidth: '220px', background: 'rgba(15,23,42,0.4)', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.04)', padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' },
  modalSectionHeading: { margin: '0 0 4px 0', fontSize: '0.85rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' },
  modalDesc: { color: '#cbd5e1', fontSize: '0.92rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', margin: 0 },
  modalMetaRow: { display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', color: '#cbd5e1', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px', alignItems: 'center' },
  modalMetaRowSelect: { display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', color: '#cbd5e1', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px', alignItems: 'center', gap: '8px' },
  modalSelect: { background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', color: '#ffffff', padding: '4px 8px', fontSize: '0.85rem', flex: 1 },

  // Status buttons
  statusButtonsGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' },
  statusBtn: { background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px', color: '#cbd5e1', padding: '8px', fontSize: '0.8rem', fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s' },
  activeStatusBtn: { background: 'rgba(99, 102, 241, 0.15)', border: '1px solid #6366f1', borderRadius: '8px', color: '#818cf8', padding: '8px', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' },
  
  deleteZone: { marginTop: '10px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.05)' },
  deleteBtn: { width: '100%', background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: '8px', color: '#fca5a5', padding: '8px', fontSize: '0.82rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.15s', ':hover': { background: 'rgba(239, 68, 68, 0.15)' } },
  
  // Forms styling
  formGrid: { display: 'flex', flexDirection: 'column', gap: '16px', width: '100%' },
  formGroup: { display: 'flex', flexDirection: 'column', gap: '6px', flex: 1 },
  formGroupFull: { display: 'flex', flexDirection: 'column', gap: '6px', width: '100%' },
  formLabel: { fontSize: '0.85rem', color: '#cbd5e1', fontWeight: 500 },
  formInput: { background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', color: '#ffffff', padding: '10px 14px', fontSize: '0.9rem' },
  formSelect: { background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', color: '#ffffff', padding: '10px 14px', fontSize: '0.9rem' },
  formTextarea: { background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', color: '#ffffff', padding: '10px 14px', fontSize: '0.9rem', resize: 'vertical' },
  
  modalFooter: { padding: '16px 20px', display: 'flex', justifyContent: 'flex-end', gap: '10px', borderTop: '1px solid rgba(255,255,255,0.06)' },
  formCancelBtn: { background: 'none', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', color: '#94a3b8', padding: '10px 20px', fontSize: '0.9rem', fontWeight: 600, cursor: 'pointer' },
  formSubmitBtn: { background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)', border: 'none', borderRadius: '10px', color: '#ffffff', padding: '10px 20px', fontSize: '0.9rem', fontWeight: 600, cursor: 'pointer' }
};
