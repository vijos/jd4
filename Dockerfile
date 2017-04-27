FROM debian:testing
COPY . root/jd4
COPY examples/langs.yaml root/.config/jd4/langs.yaml
RUN apt-get update && \
    apt-get install -y \
            gcc \
            python3 \
            python3-venv \
            python3-dev \
            g++ \
            fp-compiler \
            openjdk-8-jdk-headless \
            python \
            php7.0-cli \
            rustc \
            ghc && \
    python3 -m venv /root/venv && \
    bash -c "source /root/venv/bin/activate && \
             pip install -r /root/jd4/requirements.txt && \
             cd /root/jd4 && \
             python3 setup.py build_ext --inplace" && \
    apt-get uninstall -y python3-dev
CMD bash -c "source /root/venv/bin/activate && \
             cd /root/jd4 && \
             python3 -m jd4.daemon"
