import React, { useEffect } from 'react';

const typeStyles = {
  success: {
    icon: 'OK',
    title: 'Success',
    accent: '#10b981',
    background: 'rgba(6, 78, 59, 0.92)',
    border: 'rgba(16, 185, 129, 0.36)'
  },
  error: {
    icon: '!',
    title: 'Alert',
    accent: '#ef4444',
    background: 'rgba(127, 29, 29, 0.92)',
    border: 'rgba(239, 68, 68, 0.38)'
  },
  warning: {
    icon: '!',
    title: 'Warning',
    accent: '#f59e0b',
    background: 'rgba(120, 53, 15, 0.92)',
    border: 'rgba(245, 158, 11, 0.38)'
  },
  info: {
    icon: 'i',
    title: 'Notice',
    accent: '#38bdf8',
    background: 'rgba(12, 74, 110, 0.92)',
    border: 'rgba(56, 189, 248, 0.34)'
  }
};

function AlertNotification({ notification, onDismiss }) {
  const variant = typeStyles[notification.type] || typeStyles.info;

  useEffect(() => {
    if (notification.persist) return undefined;

    const timer = window.setTimeout(() => {
      onDismiss(notification.id);
    }, notification.duration || 4500);

    return () => window.clearTimeout(timer);
  }, [notification, onDismiss]);

  return (
    <div
      role={notification.type === 'error' ? 'alert' : 'status'}
      aria-live={notification.type === 'error' ? 'assertive' : 'polite'}
      style={{
        ...styles.toast,
        background: variant.background,
        borderColor: variant.border,
        boxShadow: `0 18px 44px rgba(0, 0, 0, 0.36), inset 3px 0 0 ${variant.accent}`
      }}
    >
      <div style={{ ...styles.icon, color: variant.accent, borderColor: variant.border }}>
        {variant.icon}
      </div>
      <div style={styles.copy}>
        <div style={styles.title}>{notification.title || variant.title}</div>
        <div style={styles.message}>{notification.message}</div>
      </div>
      <button
        type="button"
        aria-label="Dismiss notification"
        onClick={() => onDismiss(notification.id)}
        style={styles.dismissButton}
      >
        x
      </button>
    </div>
  );
}

export default function AlertNotifications({ notifications, onDismiss }) {
  if (!notifications.length) return null;

  return (
    <div style={styles.region} aria-label="Notifications">
      {notifications.map((notification) => (
        <AlertNotification
          key={notification.id}
          notification={notification}
          onDismiss={onDismiss}
        />
      ))}
    </div>
  );
}

const styles = {
  region: {
    position: 'fixed',
    top: '76px',
    right: '24px',
    zIndex: 2000,
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    width: 'min(420px, calc(100vw - 32px))',
    pointerEvents: 'none'
  },
  toast: {
    pointerEvents: 'auto',
    display: 'grid',
    gridTemplateColumns: '36px 1fr 28px',
    gap: '12px',
    alignItems: 'start',
    border: '1px solid',
    borderRadius: '8px',
    padding: '14px',
    color: '#f8fafc',
    backdropFilter: 'blur(18px)',
    animation: 'toast-slide-in 180ms ease-out',
    overflow: 'hidden'
  },
  icon: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    border: '1px solid',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.72rem',
    fontWeight: 800,
    lineHeight: 1,
    background: 'rgba(15, 23, 42, 0.38)'
  },
  copy: {
    minWidth: 0
  },
  title: {
    fontSize: '0.92rem',
    fontWeight: 700,
    marginBottom: '4px'
  },
  message: {
    color: 'rgba(248, 250, 252, 0.82)',
    fontSize: '0.86rem',
    lineHeight: 1.45,
    overflowWrap: 'anywhere'
  },
  dismissButton: {
    width: '28px',
    height: '28px',
    border: 'none',
    borderRadius: '6px',
    color: 'rgba(248, 250, 252, 0.72)',
    background: 'rgba(255, 255, 255, 0.08)',
    cursor: 'pointer',
    fontSize: '1rem',
    lineHeight: 1,
    fontWeight: 700
  }
};
