FROM python:3.11-slim

WORKDIR /app

COPY . /app

COPY requirements.txt .
RUN pip install -r requirements.txt

EXPOSE 4200

CMD ["python", "app.py"]
