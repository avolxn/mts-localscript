#!/usr/bin/env bash
set -euo pipefail

LUA_LANGUAGE_SERVER_VERSION="${LOCALSCRIPT_LUA_LANGUAGE_SERVER_VERSION:-3.18.1}"
RUNTIME_DIR="${LOCALSCRIPT_RUNTIME_DIR:-.localscript}"
TOOLS_DIR="${RUNTIME_DIR}/tools"
BIN_DIR="${RUNTIME_DIR}/bin"
INSTALL_DIR="${TOOLS_DIR}/lua-language-server-${LUA_LANGUAGE_SERVER_VERSION}"
SYMLINK_PATH="${BIN_DIR}/lua-language-server"

abspath() {
  local target="$1"
  mkdir -p "${target}"
  (
    cd "${target}"
    pwd -P
  )
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

detect_platform() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"

  case "${os}-${arch}" in
    Darwin-arm64)
      echo "darwin-arm64"
      ;;
    Darwin-x86_64)
      echo "darwin-x64"
      ;;
    Linux-arm64|Linux-aarch64)
      echo "linux-arm64"
      ;;
    Linux-x86_64)
      echo "linux-x64"
      ;;
    *)
      echo "Unsupported platform for LuaLS: ${os}-${arch}" >&2
      exit 1
      ;;
  esac
}

install_lua_language_server() {
  local platform url archive install_dir_abs
  platform="$(detect_platform)"
  url="https://github.com/LuaLS/lua-language-server/releases/download/${LUA_LANGUAGE_SERVER_VERSION}/lua-language-server-${LUA_LANGUAGE_SERVER_VERSION}-${platform}.tar.gz"
  archive="${TOOLS_DIR}/lua-language-server-${LUA_LANGUAGE_SERVER_VERSION}-${platform}.tar.gz"

  mkdir -p "${TOOLS_DIR}" "${BIN_DIR}"
  install_dir_abs="$(abspath "${INSTALL_DIR}")"

  if [[ -x "${install_dir_abs}/bin/lua-language-server" ]]; then
    rm -f "${SYMLINK_PATH}"
    ln -s "${install_dir_abs}/bin/lua-language-server" "${SYMLINK_PATH}"
    echo "LuaLS ${LUA_LANGUAGE_SERVER_VERSION} is already installed at ${INSTALL_DIR}"
    return
  fi

  rm -rf "${INSTALL_DIR}"
  rm -f "${archive}"

  echo "Downloading LuaLS ${LUA_LANGUAGE_SERVER_VERSION} for ${platform}..."
  curl -fsSL -o "${archive}" "${url}"
  mkdir -p "${INSTALL_DIR}"
  tar -xzf "${archive}" -C "${INSTALL_DIR}"
  rm -f "${archive}"
  install_dir_abs="$(abspath "${INSTALL_DIR}")"

  if [[ ! -x "${install_dir_abs}/bin/lua-language-server" ]]; then
    echo "LuaLS installation failed: ${INSTALL_DIR}/bin/lua-language-server was not found" >&2
    exit 1
  fi

  rm -f "${SYMLINK_PATH}"
  ln -s "${install_dir_abs}/bin/lua-language-server" "${SYMLINK_PATH}"
  echo "LuaLS ${LUA_LANGUAGE_SERVER_VERSION} installed at ${INSTALL_DIR}"
}

require_command curl
require_command tar
install_lua_language_server
