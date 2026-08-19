# ---------------------------------------------------------------------------
# PayrollFuturistic — Frontend (Angular) image
# ---------------------------------------------------------------------------

# ----- Dev stage (used by docker compose during development) -----
FROM node:24-alpine AS dev
WORKDIR /app

COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .

EXPOSE 4200
CMD ["npm", "run", "start:docker"]


# ----- Build stage (produces static assets for production) -----
FROM node:24-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .
RUN npm run build -- --configuration production


# ----- Production stage (nginx serving static bundle) -----
FROM nginx:1.27-alpine AS prod

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/payroll-futuristic-frontend/browser /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
