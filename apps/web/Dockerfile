FROM node:24.18.0-alpine3.23 AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@11.14.0 --activate
WORKDIR /workspace

FROM base AS dependency-cache
COPY pnpm-lock.yaml pnpm-workspace.yaml ./
RUN test "$(sha256sum pnpm-lock.yaml | cut -d ' ' -f1)" = "1910825c0e44fcb0c0d49bfda5087340071d9b6bec50bead184fd223411ac045"
RUN --mount=type=cache,id=visualengineer-web-pnpm-11.14.0-1910825c0e44fcb0c0d49bfda5087340071d9b6bec50bead184fd223411ac045,target=/pnpm/store,sharing=locked \
  pnpm fetch

FROM dependency-cache AS dependencies
COPY package.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/api-contract/package.json packages/api-contract/package.json
RUN test "$(node -p "require('./package.json').packageManager")" = "pnpm@11.14.0" \
  && test "$(pnpm --version)" = "11.14.0"
RUN --mount=type=cache,id=visualengineer-web-pnpm-11.14.0-1910825c0e44fcb0c0d49bfda5087340071d9b6bec50bead184fd223411ac045,target=/pnpm/store,sharing=locked \
  pnpm install --offline --frozen-lockfile --filter @visual-engineer/web...

FROM base AS builder
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL="$NEXT_PUBLIC_API_BASE_URL"
COPY --from=dependencies /workspace/node_modules ./node_modules
COPY --from=dependencies /workspace/apps/web/node_modules ./apps/web/node_modules
COPY --from=dependencies /workspace/packages/api-contract/node_modules ./packages/api-contract/node_modules
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web apps/web
COPY packages/api-contract packages/api-contract
RUN pnpm --filter @visual-engineer/web build

FROM node:24.18.0-alpine3.23 AS runtime
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
RUN addgroup --system --gid 1001 nodejs \
  && adduser --system --uid 1001 --ingroup nodejs nextjs
WORKDIR /app
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/.next/static ./apps/web/.next/static
USER nextjs
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3000').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"]
CMD ["node", "apps/web/server.js"]
