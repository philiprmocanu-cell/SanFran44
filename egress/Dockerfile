FROM python:3.12-slim
WORKDIR /app
COPY proxy.py allowlist.txt ./
USER 10001
CMD ["python", "-u", "proxy.py"]
