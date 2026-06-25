FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ shared/
COPY agents/__init__.py agents/__init__.py
COPY agents/token_dd/ agents/token_dd/
ENV PYTHONPATH=/app
CMD ["python", "-m", "agents.token_dd.main"]
