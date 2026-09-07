# Two ways to run this app.
#
#   --target development  the Vite dev server with hot reload, used by compose
#   (default)             the built bundle served by nginx, used when hosting
#
# The dev server must not be the hosted entrypoint: it ships unminified sources
# and refuses requests whose Host header it does not recognise, which is every
# request behind a hosting provider's domain.

FROM node:22-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install


FROM dependencies AS development
# Kept outside /app so the bind mount over the source tree cannot hide it.
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
COPY . .
EXPOSE 5173
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]


FROM dependencies AS build
COPY . .
# The API location is applied at container start, not baked in here, so this
# bundle can be deployed against any backend.
RUN npm run build


FROM nginx:1.27-alpine AS production
# The port the host asks for, and the config template that reads it. The filter
# keeps envsubst away from nginx's own $uri-style variables.
ENV PORT=8080
ENV NGINX_ENVSUBST_FILTER=PORT
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
RUN chmod +x /docker-entrypoint.d/40-runtime-config.sh
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
