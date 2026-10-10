FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir httpx fastapi uvicorn
COPY app.py guard.py ./
COPY static ./static
USER 10001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
