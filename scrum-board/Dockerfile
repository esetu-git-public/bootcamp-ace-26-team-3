# Scrum Board Dockerfile
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source code
COPY . .
RUN npm run build

# ── Serve with nginx ──────────────────────────────────────────────────────────
FROM nginx:alpine

# Copy built files to nginx html directory (Vite outputs to /app/dist)
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config for client-side routing support
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
