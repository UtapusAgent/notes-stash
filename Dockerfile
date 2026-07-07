FROM python:3.12-alpine
WORKDIR /app
COPY server.py ./
COPY public ./public
RUN mkdir -p data
EXPOSE 3000
CMD ["python3","server.py"]
