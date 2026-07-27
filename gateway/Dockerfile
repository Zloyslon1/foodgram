# Контекст сборки — корень репозитория:
# docker build -f gateway/Dockerfile -t <user>/foodgram_gateway .
FROM nginx:1.25.4-alpine

COPY gateway/nginx.conf /etc/nginx/conf.d/default.conf
COPY docs/ /usr/share/nginx/html/api/docs/
