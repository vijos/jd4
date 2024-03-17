FROM debian:bookworm
COPY . /tmp/jd4
RUN apt-get update && \
    apt-get install -y \
            gcc \
            python3 \
            python3-venv \
            python3-dev \
            g++ \
            fp-compiler \
            openjdk-17-jdk-headless \
            python-is-python3 \
            php8.2-cli \
            rustc \
            ghc \
            libjavascriptcoregtk-4.0-bin \
            golang \
            ruby \
            mono-runtime \
            mono-mcs && \
    python3 -m venv /venv && \
    bash -c "source /venv/bin/activate && \
             pip install -r /tmp/jd4/requirements.txt && \
             pip install /tmp/jd4" && \
    apt-get remove -y python3-dev && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /root/.config/jd4 && \
    cp /tmp/jd4/examples/langs.yaml /root/.config/jd4/langs.yaml && \
    rm -rf /tmp/jd4
CMD bash -c "source /venv/bin/activate && \
             python3 -m jd4.daemon"
