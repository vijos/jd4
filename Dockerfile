FROM debian:testing
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
            php7.0-cli
RUN python3 -m venv /root/venv
ADD . root/jd4
ADD examples/langs.yaml root/.config/jd4/langs.yaml
RUN bash -c "source /root/venv/bin/activate && \
             pip install -r /root/jd4/requirements.txt"
CMD bash -c "source /root/venv/bin/activate && \
             cd /root/jd4 && \
             python3 -m jd4.daemon"
