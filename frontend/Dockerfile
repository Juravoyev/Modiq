# 1-bosqich: React ilovasini yig'ish.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# 2-bosqich: tayyor fayllarni Nginx beradi, /api va /admin esa Django'ga yo'naltiriladi.
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
