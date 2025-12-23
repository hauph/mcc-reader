# Stage 1: Build Caption Inspector using their Dockerfile
FROM ubuntu:18.04 AS caption-inspector-builder

# Install dependencies for building Caption Inspector and FFMPEG
RUN apt-get update && apt-get install -y \
    autoconf \
    automake \
    build-essential \
    clang \
    cmake \
    git \
    libass-dev \
    libfreetype6-dev \
    libsdl2-dev \
    libtool \
    libva-dev \
    libvdpau-dev \
    libvorbis-dev \
    libxcb1-dev \
    libxcb-shm0-dev \
    libxcb-xfixes0-dev \
    nasm \
    pkg-config \
    texinfo \
    uuid-dev \
    wget \
    yasm \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Build FFMPEG 4.0.2 from source (required by Caption Inspector)
WORKDIR /tmp
RUN wget -q http://ffmpeg.org/releases/ffmpeg-4.0.2.tar.gz && \
    tar xzf ffmpeg-4.0.2.tar.gz && \
    cd ffmpeg-4.0.2 && \
    ./configure \
    --enable-version3 \
    --enable-hardcoded-tables \
    --enable-shared \
    --enable-static \
    --enable-small \
    --enable-libass \
    --enable-postproc \
    --enable-avresample \
    --enable-libfreetype \
    --disable-lzma \
    --enable-pthreads && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/ffmpeg*

# Clone and build Caption Inspector
WORKDIR /opt
RUN git clone https://github.com/Comcast/caption-inspector.git && \
    cd caption-inspector && \
    make caption-inspector

# Stage 2: Final image with Python
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libass9 \
    libfreetype6 \
    libva2 \
    libva-drm2 \
    libvdpau1 \
    libuuid1 \
    && rm -rf /var/lib/apt/lists/*

# Copy FFMPEG libraries from builder
COPY --from=caption-inspector-builder /usr/local/lib/libav* /usr/local/lib/
COPY --from=caption-inspector-builder /usr/local/lib/libsw* /usr/local/lib/
COPY --from=caption-inspector-builder /usr/local/lib/libpostproc* /usr/local/lib/

# Copy Caption Inspector binary
COPY --from=caption-inspector-builder /opt/caption-inspector/caption-inspector /usr/local/bin/

# Update library cache
RUN ldconfig

# Verify installation
RUN caption-inspector -h || true

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .

CMD ["python", "decoder.py"]
