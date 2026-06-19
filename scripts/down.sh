#!/usr/bin/env bash
set -euo pipefail

LUKS_MAPPER_NAME="${LUKS_MAPPER_NAME:-luks_bench}"
LUKS_PATH="${LUKS_PATH:-/mnt/luks_container}"
VERACRYPT_PATH="${VERACRYPT_PATH:-$HOME/veracrypt_container}"

if command -v veracrypt >/dev/null 2>&1; then
  if mountpoint -q "$VERACRYPT_PATH"; then
    echo "Desmontando VeraCrypt em $VERACRYPT_PATH..."
    veracrypt --text --dismount "$VERACRYPT_PATH"
  else
    echo "VeraCrypt nao esta montado em $VERACRYPT_PATH."
  fi
else
  echo "VeraCrypt nao encontrado. Pulando desmontagem do VeraCrypt."
fi

echo

if mountpoint -q "$LUKS_PATH"; then
  echo "Desmontando LUKS em $LUKS_PATH..."
  sudo umount "$LUKS_PATH"
else
  echo "LUKS nao esta montado em $LUKS_PATH."
fi

if [[ -e "/dev/mapper/$LUKS_MAPPER_NAME" ]]; then
  echo "Fechando /dev/mapper/$LUKS_MAPPER_NAME..."
  sudo cryptsetup close "$LUKS_MAPPER_NAME"
fi

echo
echo "Volumes desmontados."

