FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/src:/deps/picoweb/src:/deps/picoscript

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN git clone --depth 1 --branch picowal-c-api https://github.com/WillEastbury/picowal.git /deps/picowal \
    && git clone --depth 1 https://github.com/WillEastbury/picowal.retailprimitives.git /deps/picowal.retailprimitives \
    && git clone --depth 1 https://github.com/WillEastbury/picoweb.git /deps/picoweb \
    && git clone --depth 1 https://github.com/WillEastbury/BareMetalJsTools.git /deps/BareMetalJsTools \
    && git clone --depth 1 https://github.com/WillEastbury/picoscript.git /deps/picoscript

COPY . .

RUN mkdir -p build \
    && sed -i 's#ROOT.parent / "picoweb" / "src"#Path("/deps/picoweb/src")#' src/retail_demo_server.py \
    && sed -i 's#ROOT.parent / "BareMetalJsTools" / "src"#Path("/deps/BareMetalJsTools/src")#' src/retail_demo_server.py \
    && sed -i 's#ROOT.parent / "picoscript"#Path("/deps/picoscript")#' src/picoscript_runner.py \
    && gcc -std=c11 -Wall -Wextra -Werror -fPIC -shared \
      -DPICOWAL_HOST=1 -DPICOWAL_NO_DEFAULT_STORE=1 \
      -Isrc -I/deps/picowal/src -I/deps/picowal.retailprimitives/src \
      /deps/picowal/src/picowal_api.c \
      /deps/picowal/src/picowal_search.c \
      /deps/picowal/src/picowal_store_fs.c \
      /deps/picowal.retailprimitives/src/picowal_retail.c \
      src/demo_bridge.c \
      -lm -o build/libpicostack_retail_demo.so

EXPOSE 8080

CMD ["uvicorn", "src.retail_asgi_server:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
