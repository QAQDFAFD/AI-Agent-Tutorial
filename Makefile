.PHONY: setup test lint offline-demo graph-demo rag-demo eval-demo service capstone tutor

setup:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

offline-demo:
	uv run python -m demos.01_agent_loop.main

graph-demo:
	uv run python -m demos.04_langgraph_workflow.main

rag-demo:
	uv run python -m demos.06_rag.main

eval-demo:
	uv run python -m demos.09_quality.evaluate

service:
	uv run uvicorn demos.10_service.app:app --reload

capstone:
	uv run python -m demos.11_capstone_helpdesk.main

tutor:
	uv run uvicorn tutor.api.app:app --reload

