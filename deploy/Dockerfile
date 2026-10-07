# Builds the complete webhorus site (Pyodide wheels + Vite bundle) and serves it
# with nginx. Build context is the repository root, with submodules checked out:
#   docker build -f deploy/Dockerfile -t webhorus-web .

# Must match the pyodide version in web/yarn.lock, otherwise the wheels won't load
ARG PYODIDE_VERSION=0.29.0

# ── Stage 1: cross-compile the Python packages to WebAssembly ──
FROM python:3.13 AS wheels
ARG PYODIDE_VERSION
RUN pip install --no-cache-dir 'pyodide-build[resolve]' && \
    pyodide xbuildenv install ${PYODIDE_VERSION}
RUN git clone --depth 1 https://github.com/emscripten-core/emsdk.git /emsdk && \
    cd /emsdk && \
    ./emsdk install $(pyodide config get emscripten_version) && \
    ./emsdk activate $(pyodide config get emscripten_version)

WORKDIR /webhorus
# Only the Python sources, so web-only changes reuse the cached wheels
COPY pyproject.toml poetry.lock build_lib.py README.md ./
COPY pywenet pywenet
COPY webhorus webhorus
COPY horusdemodlib horusdemodlib
COPY wenet wenet
COPY ssdv ssdv
RUN bash -c 'source /emsdk/emsdk_env.sh && \
    pyodide build --build-dependencies --no-skip-built-in-packages --outdir /whl/'

# ── Stage 2: build the web app ──
FROM node:23 AS web
WORKDIR /webhorus/web
COPY web/package.json web/yarn.lock web/.yarnrc.yml ./
RUN corepack enable && yarn install --immutable
COPY web/ ./
COPY --from=wheels /whl/ ./src/whl/
# the production build (sourcemaps for plotly/pyodide) needs more than the default heap
RUN NODE_OPTIONS=--max-old-space-size=6144 yarn build

# ── Stage 3: serve ──
FROM nginx:alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=web /webhorus/web/src/dist /usr/share/nginx/html
