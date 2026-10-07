#!/usr/bin/env bash
# Build webhorus on the NAS and (re)start its Dockge stack.
# The site is served publicly through Tailscale Funnel at https://webhorus.<tailnet>.ts.net
set -e

NAS_HOST="${NAS_HOST:-truenas_admin@192.168.3.143}"
NAS_STACK_DIR="/mnt/MainPool/Dockge/Stacks/webhorus"
IMAGE_NAME="webhorus-web"
SRC_TAR="webhorus-src.tar.gz"

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$DEPLOY_DIR/.." && pwd)"
VERSION="$(git -C "$REPO_DIR" rev-parse --short HEAD)"

if [ -n "$(git -C "$REPO_DIR" status --porcelain --untracked-files=no)" ]; then
    echo "!! Uncommitted changes are not deployed — only HEAD ($VERSION) is packaged."
fi

# ── Step 1: Package committed source, including submodules ──
# git archive reads from git objects, so cloud-sync placeholder files in the
# working tree don't matter (docker can't follow those reparse points).
BUILD_TMP="$(mktemp -d)"
trap 'rm -rf "$BUILD_TMP" "$DEPLOY_DIR/$SRC_TAR"' EXIT
echo "==> Packaging $VERSION..."
git -C "$REPO_DIR" archive HEAD | tar -x -C "$BUILD_TMP"
git -C "$REPO_DIR" submodule foreach --quiet \
    "git archive --prefix=\"\$sm_path/\" HEAD | tar -x -C \"$BUILD_TMP\""
tar -C "$BUILD_TMP" -czf "$DEPLOY_DIR/$SRC_TAR" .

# ── Step 2: Transfer to NAS ──
echo "==> Uploading to NAS..."
scp "$DEPLOY_DIR/$SRC_TAR" "$NAS_HOST:/tmp/$SRC_TAR"
scp "$DEPLOY_DIR/compose.nas.yml" "$NAS_HOST:/tmp/webhorus-compose.yml"
scp "$DEPLOY_DIR/tailscale-config/serve.json" "$NAS_HOST:/tmp/webhorus-serve.json"

# ── Step 3: Build image on NAS, recreate containers ──
echo "==> Building and deploying on NAS (first build takes a while: emsdk + wheels)..."
ssh "$NAS_HOST" "IMAGE_NAME='$IMAGE_NAME' VERSION='$VERSION' STACK='$NAS_STACK_DIR' bash -s" <<'REMOTE'
set -e
rm -rf /tmp/webhorus-build
mkdir -p /tmp/webhorus-build
tar -C /tmp/webhorus-build -xzf /tmp/webhorus-src.tar.gz

echo "    Building image..."
sudo docker build -f /tmp/webhorus-build/deploy/Dockerfile \
    -t "$IMAGE_NAME:$VERSION" -t "$IMAGE_NAME:latest" /tmp/webhorus-build

echo "    Updating stack files..."
sudo mkdir -p "$STACK/tailscale-config"
sudo cp /tmp/webhorus-compose.yml "$STACK/compose.yaml"
sudo cp /tmp/webhorus-serve.json "$STACK/tailscale-config/serve.json"
sudo touch "$STACK/.env" # TS_AUTHKEY=... may be added here; optional

echo "    Starting containers..."
cd "$STACK"
sudo docker compose up -d --force-recreate web
sudo docker compose up -d tailscale

echo "    Cleaning up..."
rm -rf /tmp/webhorus-build /tmp/webhorus-src.tar.gz /tmp/webhorus-compose.yml /tmp/webhorus-serve.json
sudo docker image prune -f
REMOTE

echo ""
echo "==> Deployed $VERSION"
echo "    If this is the first deploy, authorise the node with the URL from:"
echo "      ssh $NAS_HOST sudo docker logs webhorus-tailscale 2>&1 | grep login.tailscale.com"
