# Row A Process Historian (MW-HIST-01). SQLite-backed trend-report web app on :80.
# On the OT network only -- reachable from the dual-homed EWS, not from the host.
# Stdlib only (http.server + sqlite3); nothing fetched at run time.
FROM python:3.12-slim
WORKDIR /opt/historian
COPY app.py .
EXPOSE 80
# Seed the DB on first start, then serve. Runs as root only to bind :80 in-container.
CMD ["python", "-u", "app.py"]
