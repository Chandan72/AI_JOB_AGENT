FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt

RUN mkdir -p outputs candidate_data cache job_hunter

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]
