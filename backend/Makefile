dev:
	uv run uvicorn app.main:app --reload

worker:
	uv run celery -A app.worker worker --loglevel=info