#!/bin/bash
#
# Runs a basic end-to-end test under multiple versions of Python.
#
# Tests from 'pip install' through to first time user scenario,
# using Docker containers to provide isolation.
#
set -e
if [[ ! "awsmfa" == "$(basename "$(pwd)")" ]]; then
  echo run this script from the awsmfa/ directory
  exit 2
fi
DIST_DIR=$(mktemp -d)
python setup.py sdist -d "${DIST_DIR}"
RELEASE=awsmfa-$(head -1 awsmfa/_version.py|cut -f4 -d\").tar.gz
echo __ testing release "${RELEASE}"
# Python.org (https://hub.docker.com/_/python/)
IMAGES="python:2.7-alpine python:3.3-alpine python:3.4-alpine python:3.5-alpine"
# PyPy (https://hub.docker.com/_/pypy/). Not including 3 due to an
# incompatibility with the six module.
IMAGES="${IMAGES} pypy:2"
echo __ testing versions "${IMAGES}"
TEST_SCRIPT=$(cat <<END
chown root:root /pipcache && \
pip install --cache-dir /pipcache awscli ${RELEASE} && \
awsmfa -h && \
awsmfa --version && \
aws configure --profile identity set aws_access_key_id AKIA && \
aws configure --profile identity set aws_secret_access_key SECRET && \
cat /root/.aws/credentials && \
AWSMFA_TESTING_MODE=Yup awsmfa && \
cat /root/.aws/credentials && \
grep -q '\[default\]' /root/.aws/credentials && \
grep -q awsmfa_expiration /root/.aws/credentials
END
)
PIP_CACHE="${VIRTUAL_ENV}/pipcache"
mkdir -p "${PIP_CACHE}" || /bin/true
echo __ test script: "${TEST_SCRIPT}"
LOG_DIR=$(mktemp -d)
echo Logging to: "${LOG_DIR}"
for IMAGE in ${IMAGES}; do
  LOG_FILE=${LOG_DIR}/log-${IMAGE}
  (echo __ starting "${IMAGE}" ; if docker run -t --rm \
      -w /usr/src/myapp \
      -e PIP_DOWNLOAD_CACHE=/pipcache \
      -v "${PIP_CACHE}:/pipcache" \
      -v "${DIST_DIR}:/usr/src/myapp" \
      "${IMAGE}" \
      /bin/sh -x -e -c "${TEST_SCRIPT}" > "${LOG_FILE}" 2>&1; then
    echo "${IMAGE}" PASSED
  else
    echo "${IMAGE}" FAILED
  fi) &
done
echo __ waiting for tests to complete
wait
