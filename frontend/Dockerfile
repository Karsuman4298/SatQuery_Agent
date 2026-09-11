# ============================================================
# SatQuery AI — Dockerfile
# Multi-stage build
#
# Stage 1 (builder): Node 22 Alpine — installs dependencies,
#                    runs `npm run build` to produce dist/
# Stage 2 (runner):  Nginx Alpine — serves the static SPA
#                    with proper fallback for client-side
#                    routing (React Router v7)
# ============================================================

# ─── Stage 1: Build ─────────────────────────────────────────
FROM node:22-alpine AS builder

# Set working directory
WORKDIR /app

# Copy dependency manifests first (layer-caching: only re-installs
# when package.json / package-lock.json actually change)
COPY package.json package-lock.json ./

# Install all dependencies (including devDependencies needed for build)
RUN npm ci

# Copy the rest of the source
COPY . .

# Build production bundle → outputs to /app/dist
RUN npm run build

# ─── Stage 2: Serve ─────────────────────────────────────────
FROM nginx:1.27-alpine AS runner

# Remove the default Nginx placeholder page
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets from stage 1
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our custom Nginx config (handles SPA fallback routing)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 (Nginx default)
EXPOSE 80

# Start Nginx in the foreground (required for Docker)
CMD ["nginx", "-g", "daemon off;"]
