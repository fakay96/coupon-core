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
npm run test --prefix frontend
```
If Django or GDAL is missing, or if Vitest isn't installed, the affected tests
are automatically skipped so the suite can still complete.
Pytest automatically uses the `coupon_core.settings.test` configuration, which
relies on in-memory SQLite databases so no additional services are required.
GeoDjango looks for the GDAL library at `/usr/lib/x86_64-linux-gnu/libgdal.so`.
If it isn't available system-wide, set `GDAL_LIBRARY_PATH` to that file and
prepend `/usr/lib/x86_64-linux-gnu` to `LD_LIBRARY_PATH` before running tests.
To run tests against PostgreSQL instead, start the containers with
`docker-compose up postgres` and set
`DJANGO_SETTINGS_MODULE=coupon_core.settings` before running `pytest`.

The `test` workflow fails if backend coverage drops below **90%**. Tests use
SQLite databases by default so they can run locally without PostgreSQL.

You can also run the tests inside containers using `run_tests.sh` which relies
on `docker-compose`. This script starts the required services with dummy data,
runs migrations and executes the full test suite with coverage.

## Continuous Integration

All pull requests trigger the `test` workflow which runs the Python and
JavaScript test suites. The `ci` workflow waits for these tests to pass before
building Docker images and deploying. Deployments default to the `staging`
environment unless specified otherwise when manually triggering the workflow.

