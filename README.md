# Notes App

A real notes editor with search, tags, pinning, and Markdown preview.

Transparent note: this tiny demo was generated and maintained by UtapusAgent automation.

## Screenshot

![App screenshot](docs/screenshot.png)

## Usage

```sh
npm start
# or
PORT=3000 docker compose up --build
```

Open <http://localhost:3000>. Data is stored in SQLite at `data/app.db`.

## Features

- Two-pane notes editor
- Live Markdown preview
- Search, tags, and pinned notes
- JSON backup export
- SQLite persistence

## Use Cases

- Personal knowledge base
- Lightweight customer notes portal
- Self-hosted Markdown notebook

## Development

Run the local verification checks before opening a pull request:

```sh
python3 -m py_compile server.py
node --check public/app.js
node --check public/config.js
./scripts/smoke_test.sh
```

## Real Integrations

The app stores user-created data locally in SQLite and does not upload records to external services.

## Customer Deployment Notes

- Run with Docker Compose for persistence and restart behavior.
- Back up `data/app.db` or use the in-app JSON export before upgrades.
- External integrations are read-only GET requests; user-created records remain in local SQLite.
- The container includes a healthcheck at `/health`.
