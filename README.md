# coupon-core

This repository contains the backend and frontend code for the coupon service.
The backend is built with Django while the frontend uses Vite and TypeScript.

## Running tests

Install Python and Node dependencies:

```bash
pip install -r req.txt
npm ci --prefix frontend
```

Run the backend and frontend test suites:

```bash
pytest -q
npm run test --prefix frontend -- --run
```

The `test` workflow fails if backend coverage drops below **90%**. Tests use
SQLite databases by default so they can run locally without PostgreSQL.

## Continuous Integration

All pull requests trigger the `test` workflow which runs the Python and
JavaScript test suites. The `ci` workflow waits for these tests to pass before
building Docker images and deploying. Deployments default to the `staging`
environment unless specified otherwise when manually triggering the workflow.

