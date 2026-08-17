FROM nvidia/cuda:12.5.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential ca-certificates curl git make python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir \
      matplotlib==3.9.1 numpy==1.26.4 pillow==10.4.0

WORKDIR /workspace/LongTarget-exact-sim
COPY . .

CMD ["bash", "reproduce/check_reproduction.sh"]
