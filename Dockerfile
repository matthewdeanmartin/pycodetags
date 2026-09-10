# Linux release validation; no package publishing or source mutation.
ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim
WORKDIR /workspace
RUN python -m pip install --no-cache-dir uv
COPY . .
RUN uv pip install --system . pytest pytest-cov hypothesis jinja2
RUN python -m pytest tests --cov=pycodetags --cov-fail-under=65
RUN python scripts/release_candidates.py all
RUN uv pip install --system ./plugins/pycodetags_issue_tracker ./plugins/pycodetags_chat ./plugins/pycodetags_universal
RUN python -m pytest plugins/pycodetags_issue_tracker/tests plugins/pycodetags_chat/tests plugins/pycodetags_universal/tests --import-mode=importlib
CMD ["python", "-m", "pycodetags", "--help"]
