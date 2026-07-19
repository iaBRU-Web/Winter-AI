# Building the Real Mercury Compiler (Optional, Advanced)

Mercury's compiler (`mmc`) has no maintained apt/deb package on modern
Ubuntu/Debian. The only path is building from source which takes 30-60
minutes and several hundred MB -- impractical for a Render Docker build.

This is why `determinism.py` in this folder is an honest Python
re-implementation of Mercury's determinism categories instead of a fake
subprocess call to a compiler that would never install.

If you want to attempt a real build:

```dockerfile
FROM ubuntu:22.04 AS mercury-builder
RUN apt-get update && apt-get install -y build-essential wget flex bison
WORKDIR /mercury-src
# Get current release URL from https://mercurylang.org/download.html
RUN wget https://dl.mercurylang.org/release/mercury-srcdist-VERSION.tar.gz \
    && tar xzf mercury-srcdist-VERSION.tar.gz
WORKDIR /mercury-src/mercury-VERSION
RUN ./configure --prefix=/opt/mercury && make -j$(nproc) && make install
```

Then copy `/opt/mercury` into the final image and add to `PATH`.
