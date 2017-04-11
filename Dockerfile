FROM debian:testing
COPY . root/jd4
COPY examples/langs.yaml root/.config/jd4/langs.yaml
RUN apt-get update && \
    apt-get install -y \
            gcc \
            python3 \
            python3-venv \
            python3-dev \
            libffi-dev \
            g++ \
            fp-compiler \
            openjdk-8-jdk-headless \
            python \
            php7.0-cli && \
    python3 -m venv /root/venv && \
    bash -c "source /root/venv/bin/activate && \
             pip install -r /root/jd4/requirements.txt" && \
    apt-get remove -y \
            python3-dev \
            libffi-dev && \
    apt-get autoremove -y
CMD bash -c "source /root/venv/bin/activate && \
             cd /root/jd4 && \
             python3 -m jd4.daemon"
