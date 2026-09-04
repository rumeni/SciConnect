FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

# Kept outside /app so the bind mount over the source tree cannot hide it.
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

COPY . .

EXPOSE 5173
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
