FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    openssh-server \
    docker.io \
    curl

RUN mkdir /var/run/sshd

RUN useradd -m -s /bin/bash player && \
    echo "player:player" | chpasswd

RUN usermod -aG docker player

RUN echo "AllowUsers player" >> /etc/ssh/sshd_config && \
    echo "PermitRootLogin no" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "AllowAgentForwarding no" >> /etc/ssh/sshd_config && \
    echo "AllowTcpForwarding no" >> /etc/ssh/sshd_config && \
    echo "X11Forwarding no" >> /etc/ssh/sshd_config && \
    echo 'ForceCommand docker run --rm -it --network none --memory 128m --cpus 0.5 --pids-limit 50 --user player ingehack.azurecr.io/challs/screw-cryptography-inner:latest' >> /etc/ssh/sshd_config

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 6767
CMD ["/entrypoint.sh"]
