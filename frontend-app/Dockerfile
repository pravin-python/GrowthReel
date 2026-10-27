# syntax=docker/dockerfile:1

# ---- Build stage -----------------------------------------------------------
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
# Real build-time env (VITE_* vars are baked into the bundle at build time).
# Override with --build-arg / a .env file as needed; VITE_USE_MOCKS defaults
# to unset so production bundles never include/activate the mock layer logic
# path intentionally (it's still code-split in, but never installed).
RUN npm run build

# ---- Runtime stage ----------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

# Run as a non-root user.
RUN addgroup -g 1001 -S appgroup \
  && adduser -u 1001 -S appuser -G appgroup \
  && chown -R appuser:appgroup /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx \
  && touch /var/run/nginx.pid \
  && chown appuser:appgroup /var/run/nginx.pid

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build --chown=appuser:appgroup /app/dist /usr/share/nginx/html

USER appuser
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
