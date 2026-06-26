FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
ENV PORT=10000
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    swi-prolog \
    g++ \
    ocaml \
    sbcl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    fastapi==0.115.5 \
    pydantic==2.10.3 \
    uvicorn==0.32.1 \
    python-multipart==0.0.9 \
    aiofiles==23.2.1

WORKDIR /app
COPY . .

RUN chmod -R 755 /app/api/info && \
    chmod 644 /app/api/brain.txt

EXPOSE 10000

CMD uvicorn api.index:app --host 0.0.0.0 --port ${PORT}
