FROM python:3.12-alpine
WORKDIR /app
COPY server.py ./
COPY public ./public
RUN mkdir -p data && adduser -D appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/health', timeout=2).read()"
CMD ["python3","server.py"]
