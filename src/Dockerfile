FROM python:3.13-slim

WORKDIR /app

RUN pip install fastapi mlflow==2.20.2 psutil==7.0.0

EXPOSE 8083

CMD ["python", "app.py"]
