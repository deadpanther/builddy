# ── Stage 1: Install ALL dependencies (needed for build) ──────────
FROM node:20-bookworm-slim AS deps

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install all deps (dev deps needed for build step)
RUN npm ci --legacy-peer-deps

# ── Stage 2: Build the application ─────────────────────────────────
FROM node:20-bookworm-slim AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Next.js collects anonymous telemetry — disable it
ENV NEXT_TELEMETRY_DISABLED=1

# Build arguments baked in at build time for Next.js public env vars
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_AUTOPSY_URL=http://localhost:8001
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_AUTOPSY_URL=$NEXT_PUBLIC_AUTOPSY_URL

RUN npm run build

# ── Stage 3: Production runtime ────────────────────────────────────
FROM node:20-bookworm-slim AS runner

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built assets from builder
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Fix ownership
RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

ENV PORT=3000 \
    HOSTNAME="0.0.0.0"

# Railway sets $PORT dynamically
CMD ["sh", "-c", "PORT=${PORT:-3000} node server.js"]
