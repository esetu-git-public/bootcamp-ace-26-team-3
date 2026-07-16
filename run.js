const { spawn } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

const isWindows = os.platform() === 'win32';

// 1. Resolve Python executable inside the virtual environment (.venv)
let pythonExec = isWindows 
  ? path.join(__dirname, '.venv', 'Scripts', 'python.exe')
  : path.join(__dirname, '.venv', 'bin', 'python');

if (!fs.existsSync(pythonExec)) {
  console.warn(`[System] Virtual environment not found at: ${pythonExec}`);
  console.warn(`[System] Attempting to fall back to system 'python' or 'python3'...`);
  pythonExec = isWindows ? 'python' : 'python3';
}

console.log(`[System] Using Python executable: ${pythonExec}`);

// Helper to spawn processes with shared stdio to maintain terminal formatting/colors
function startService(name, command, args, cwd, envExtra = {}, useShell = false) {
  console.log(`[System] Starting ${name} service...`);
  
  const child = spawn(command, args, {
    cwd,
    shell: useShell,
    stdio: 'inherit',
    env: { ...process.env, ...envExtra }
  });

  child.on('error', (err) => {
    console.error(`[System Error] Failed to start service ${name}:`, err);
  });

  return child;
}

// 2. Start Backend
const backendProcess = startService(
  'Backend',
  pythonExec,
  ['-m', 'uvicorn', 'backend.app.main:app', '--host', '0.0.0.0', '--port', '8000', '--reload'],
  __dirname,
  {
    PYTHONPATH: '.',
    DATABASE_URL: 'sqlite:///./app.db'
  },
  false // shell: false for python prevents quoting issues with paths containing spaces
);

// 3. Start Frontend
const frontendProcess = startService(
  'Frontend',
  'npm',
  ['start'],
  path.join(__dirname, 'frontend'),
  {
    CLEAR_CONSOLE: 'false' // stops react-scripts from clearing logs of other services
  },
  true // shell: true needed for npm execution on Windows
);

// Clean up processes on exit
const cleanExit = () => {
  console.log('\n[System] Stopping all services...');
  try { backendProcess.kill(); } catch (e) {}
  try { frontendProcess.kill(); } catch (e) {}
  process.exit(0);
};

process.on('SIGINT', cleanExit);
process.on('SIGTERM', cleanExit);
process.on('exit', cleanExit);
