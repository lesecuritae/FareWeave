FROM node:24-bookworm-slim AS db-vendo-builder
ARG DB_VENDO_COMMIT=5afe12a80e02cf111f38f3fa30ae87aaa532d1d6
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git init db-vendo-client \
    && cd db-vendo-client \
    && git remote add origin https://github.com/public-transport/db-vendo-client.git \
    && git fetch --depth 1 origin "${DB_VENDO_COMMIT}" \
    && git checkout --detach FETCH_HEAD \
    && npm ci --omit=dev --ignore-scripts

FROM node:24-bookworm-slim
ENV NODE_ENV=production
WORKDIR /app
COPY --from=db-vendo-builder /src/db-vendo-client ./vendor
COPY --from=db-vendo-builder /src/db-vendo-client/LICENSE.md /usr/share/licenses/db-vendo-client/LICENSE.md
COPY server.mjs ./server.mjs
USER node
EXPOSE 3001
CMD ["node", "/app/server.mjs"]
