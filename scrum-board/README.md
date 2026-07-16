# Scrum Board

This is the standalone Scrum Board application built with React + Vite.

## Running the Scrum Board (Standalone)

To run **only** the Scrum Board, execute the following commands from the repository root:

```bash
cd scrum-board
npm install
npm run dev
```

Once started, the Scrum Board UI will be available at:
* **Local:** http://localhost:5173

---

### Alternative: Using Docker

If you prefer to run it inside a Docker container:

1. **Build the container:**
   ```bash
   docker build -t scrum-board ./scrum-board
   ```
2. **Run the container:**
   ```bash
   docker run -p 5173:80 scrum-board
   ```
   *(The Scrum Board will then be accessible at http://localhost:5173)*
