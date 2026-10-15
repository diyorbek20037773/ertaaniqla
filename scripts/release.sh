#!/usr/bin/env bash
# Moving code between the environments (D-088, RUNBOOK «CI/CD and environments»).
#   release.sh promote           main → stage, fast-forward only: staging receives exactly the
#                                commit (and image) that ran on dev; CI then deploys staging.
#   release.sh release v1.4.0    GitHub Release of the current `stage` commit; release.yml checks
#                                that staging ran it, promotes its image and waits for the prod
#                                approval.
# Env: MAIN_BRANCH (default master — this repository's main branch).
set -euo pipefail
MAIN="${MAIN_BRANCH:-master}"
CMD="${1:?promote | release vX.Y.Z}"

git fetch --quiet --tags origin

case "${CMD}" in
  promote)
    target="$(git rev-parse "origin/${MAIN}")"
    if git rev-parse --verify --quiet origin/stage >/dev/null; then
      if ! git merge-base --is-ancestor origin/stage "${target}"; then
        echo "stage has commits that are not on ${MAIN} — merge them back into ${MAIN} first" >&2
        exit 1
      fi
    fi
    git push origin "${target}:refs/heads/stage"
    echo "stage → ${target:0:12}; CI deploys it to staging for QA"
    ;;
  release)
    VERSION="${2:?release vX.Y.Z}"
    [[ "${VERSION}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "version must look like v1.2.3" >&2; exit 1; }
    if git rev-parse --verify --quiet "refs/tags/${VERSION}" >/dev/null; then
      echo "${VERSION} already exists" >&2; exit 1
    fi
    target="$(git rev-parse origin/stage)"
    gh release create "${VERSION}" --target "${target}" --title "${VERSION}" --generate-notes
    echo "${VERSION} → ${target:0:12}; release.yml deploys it to prod after approval"
    ;;
  *)
    echo "unknown command: ${CMD} (promote | release vX.Y.Z)" >&2; exit 2
    ;;
esac
