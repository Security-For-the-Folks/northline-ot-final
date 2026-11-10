# Engineering Workstation (MW-ENG-01).
# IT-side services: a commissioning web portal (:80) and SSH (:22).
# Dual-homed onto the OT network by compose. All tools baked at build time.
FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server \
        python3 \
        python3-pip \
        nmap \
        mbpoll \
        iproute2 \
        iputils-ping \
        netcat-openbsd \
        less \
    && rm -rf /var/lib/apt/lists/*

# Real industry Modbus client + interactive console (the `[repl]` extra ships the
# `pymodbus.console` command). Debian-12-slim pip is PEP-668 externally-managed,
# so --break-system-packages is required. Baked at build time: no runtime internet.
RUN pip3 install --no-cache-dir --break-system-packages "pymodbus[repl]==3.7.0" "pymodbus-repl==2.0.4"

ARG EWS_USER=svc_maint
ARG EWS_PASS=trustno1
RUN useradd -m -s /bin/bash ${EWS_USER} \
    && echo "${EWS_USER}:${EWS_PASS}" | chpasswd

RUN mkdir -p /run/sshd \
    && sed -i 's/#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed -i 's/#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && ssh-keygen -A

COPY portal/ /opt/portal/
RUN chmod +x /opt/portal/portal.py

COPY home/ /home/svc_maint/
RUN chown -R svc_maint:svc_maint /home/svc_maint

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 22 80
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
