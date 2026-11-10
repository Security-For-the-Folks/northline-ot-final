# IT-network toolbox host. All tools baked in at build time so the
# container needs NO internet at run time (it is on an internal network).
FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        nmap \
        curl \
        john \
        sqlmap \
        openssh-client \
        sshpass \
        python3 \
        iproute2 \
        iputils-ping \
        netcat-openbsd \
        less \
        vim-tiny \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/share/wordlists
COPY wordlists/rockyou-lite.txt /usr/share/wordlists/rockyou-lite.txt

WORKDIR /root
COPY motd /etc/motd
RUN echo '[ -f /etc/motd ] && cat /etc/motd' >> /root/.bashrc

CMD ["sleep", "infinity"]
