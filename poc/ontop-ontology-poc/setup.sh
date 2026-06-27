#!/usr/bin/env bash
# Download the (pinned, checksum-verified) Ontop CLI toolchain for this POC.
# All artifacts land under tools/ and are gitignored. Re-runnable / idempotent.
set -euo pipefail

ONTOP_VERSION="5.5.0"
SQLITE_JDBC_VERSION="3.49.1.0"

# SHA-256 checksums of the pinned downloads (reproducibility guard).
ONTOP_ZIP_SHA256="430dff312e68e8ad41d26e6113160ca2365c28c4fe911926193000a33299458f"
SQLITE_JDBC_SHA256="5c8609d2ca341deb8c6f71778974b5ba4995c7d32d7c7c89d9392a3e72c39291"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS="${SCRIPT_DIR}/tools"
ONTOP_DIR="${TOOLS}/ontop-cli-${ONTOP_VERSION}"

mkdir -p "${TOOLS}"

verify() {  # verify <file> <expected-sha256>
  echo "${2}  ${1}" | sha256sum -c - >/dev/null
}

if [ ! -x "${ONTOP_DIR}/ontop" ]; then
  echo "Downloading Ontop CLI ${ONTOP_VERSION}..."
  ZIP="${TOOLS}/ontop-cli-${ONTOP_VERSION}.zip"
  curl -fL -o "${ZIP}" \
    "https://github.com/ontop/ontop/releases/download/ontop-${ONTOP_VERSION}/ontop-cli-${ONTOP_VERSION}.zip"
  echo "Verifying checksum..."
  verify "${ZIP}" "${ONTOP_ZIP_SHA256}"
  mkdir -p "${ONTOP_DIR}"
  (cd "${ONTOP_DIR}" && unzip -oq "../ontop-cli-${ONTOP_VERSION}.zip")
  chmod +x "${ONTOP_DIR}/ontop"
else
  echo "Ontop CLI ${ONTOP_VERSION} already present."
fi

JDBC_JAR="${ONTOP_DIR}/jdbc/sqlite-jdbc-${SQLITE_JDBC_VERSION}.jar"
if [ ! -f "${JDBC_JAR}" ]; then
  echo "Downloading sqlite-jdbc ${SQLITE_JDBC_VERSION}..."
  curl -fL -o "${JDBC_JAR}" \
    "https://repo1.maven.org/maven2/org/xerial/sqlite-jdbc/${SQLITE_JDBC_VERSION}/sqlite-jdbc-${SQLITE_JDBC_VERSION}.jar"
  echo "Verifying checksum..."
  verify "${JDBC_JAR}" "${SQLITE_JDBC_SHA256}"
else
  echo "sqlite-jdbc ${SQLITE_JDBC_VERSION} already present."
fi

echo "Toolchain ready. Java runtime required (java -version): $(java -version 2>&1 | head -1)"
