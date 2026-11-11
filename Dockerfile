# The app in a container: docker compose up --build, then open http://localhost:8501
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Dependencies first, so editing the code doesn't reinstall them on every build.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY .streamlit ./.streamlit
COPY src ./src
RUN uv sync --locked --no-dev

EXPOSE 8501
# 0.0.0.0 so the app is reachable from outside the container.
CMD ["uv", "run", "--no-sync", "finance-analyzer", "--server.address=0.0.0.0", "--server.headless=true"]
