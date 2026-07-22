# Adaptive Assessment — frontend (Next.js). Multi-stage: Next.js's build step needs the full
# node_modules + compiler toolchain, but the actual RUNNING app only needs a tiny slice of that
# (Next.js's `output: "standalone"` mode bundles just what's needed). Building in one stage and
# running from a second, much leaner one keeps the final image small without giving up the
# ability to build at all.

# ---- deps: install once, cached separately from source changes ----
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- builder: compile the actual app ----
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Baked into the client bundle at BUILD time (Next.js inlines NEXT_PUBLIC_* vars into the
# browser bundle, not read at runtime) — override via `docker compose build --build-arg` if the
# frontend needs to reach the backend somewhere other than the default. Left at its default here
# because in the common case (both containers' ports published to the host) it's the *browser*
# on the host making these calls to localhost:8000, not container-to-container traffic.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
RUN npm run build

# ---- runner: the actual production image, only what's needed to run ----
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Run as a non-root user (Next.js's own convention for this exact setup).
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# `output: "standalone"` produces a minimal server.js + only the node_modules actually needed —
# but it does NOT automatically include static assets or the public/ folder, so those are copied
# in explicitly (a common gotcha with this Next.js output mode).
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]