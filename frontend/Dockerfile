FROM node:20-alpine

WORKDIR /app

# NEXT_PUBLIC_* vars are inlined at build time, so the API URL is a build arg.
# The browser calls the host-mapped backend port, hence localhost by default.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    HOSTNAME=0.0.0.0 \
    NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Normal (non-static) production build so `next start` can serve the app.
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
