# Simulated Schneider ATV630 VFD (Modbus/TCP target)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY config.py atv630.py main.py ./
# Modbus/TCP
EXPOSE 502
CMD ["python", "-u", "main.py"]
