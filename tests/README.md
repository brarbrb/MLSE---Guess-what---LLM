# Testing Overview

This folder contains all automated tests for the Guess What project.
Tests are organized by scope — from unit-level database checks to full-stack integration and stress scenarios.

In addition we performed e2e testing manually: frontend, templates, buttons dark mode and bright mode. 

## Folder Structure


| Folder / File | Purpose |
|----------------|----------|
| `tests/unit/` | Tests for isolated modules — mainly **SQLAlchemy models**, helper functions, and validation logic. |
| `tests/integration/` | Tests the **Flask API endpoints** (`/api/users`, `/api/health`, etc.) using a live test client and temporary database. |
| `tests/security/` | Verifies **access control**, session handling, and rejection of unauthorized or malformed requests. |
| `tests/stress/` | **Locust** load-testing scripts that simulate hundreds of concurrent users and malformed inputs under stress. |


## Running tests 🏃‍♀️
All tests are run from root folder! 

1. Pytest
   Run with
   `pytest -v ` - (-q for headless).

    This tests:
   ```
   pytest tests/unit
    pytest tests/integration
    pytest tests/security
    ```
2. Stress tests  💪

Note: That for these tests there's need to run the flask app!

```bash
  $ locust -f tests/stress/locustfile_heavy.py --headless -t 60s --host http://localhost:8000
  
  $ locust -f tests/stress/locustfile.py --headless -u 50 -r 20 -t 30s --host http://localhost:8000
  ```

## Dependencies 
Since we used the dependencies (pytest, sqlalchemy etc.) there's need to istall Dependencies. Run this code: 
```
   
```
