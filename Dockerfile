FROM debian:stretch
COPY . /tmp/jd4
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
            haskell-platform \
            libjavascriptcoregtk-4.0-bin \
            golang \
            ruby \
            mono-runtime \
            mono-mcs \
            axel && \
    python3 -m venv /venv && \
    bash -c "source /venv/bin/activate && \
             pip install -r /tmp/jd4/requirements.txt && \
             pip install /tmp/jd4" && \
    apt-get remove -y python3-dev && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /root/.config/jd4 && \
    cp /tmp/jd4/examples/langs.yaml /root/.config/jd4/langs.yaml && \
    rm -rf /tmp/jd4 && \
    axel https://julialang-s3.julialang.org/bin/linux/x64/1.0/julia-1.0.0-linux-x86_64.tar.gz && \
    tar xf julia-1.0.0-linux-x86_64.tar.gz --strip-components=1 -C /usr && \
    rm julia-1.0.0-linux-x86_64.tar.gz
CMD bash -c "source /venv/bin/activate && \
             python3 -m jd4.daemon"
