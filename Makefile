.PHONY: test backend-test frontend-test

# Run the complete offline test suite after dependencies have been installed.
test: backend-test frontend-test

backend-test:
	@if [ -x backend/.venv/bin/pytest ]; then cd backend && .venv/bin/pytest -q; else cd backend && python -m pytest -q; fi

frontend-test:
	cd frontend && npm test
