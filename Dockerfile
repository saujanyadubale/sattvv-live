FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY satvv/ satvv/
COPY web/ web/
COPY docs/ docs/
RUN useradd -m -u 10001 satvv && chown -R satvv:satvv /app
USER satvv
EXPOSE 10000
CMD ["python","-m","satvv.deployment_server"]
