FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir anthropic httpx fastapi uvicorn
COPY agent.py tools.py ./
ENV HOME=/tmp
USER 10001
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "9000"]
