# Contributing

Thanks for improving this tiny demo app.

## Local checks

```sh
python3 -m py_compile server.py
node --check public/app.js
node --check public/config.js
./scripts/smoke_test.sh
```

## Pull requests

- Keep changes small and focused.
- Update the README when usage or features change.
- Avoid committing `data/app.db`; it is runtime state.
