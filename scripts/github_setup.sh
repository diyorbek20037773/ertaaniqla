#!/usr/bin/env bash
# One-time GitHub settings for the CI/CD flow (D-088). Needs `gh auth login` with admin rights.
#   REVIEWERS="login1 login2" bash scripts/github_setup.sh
# Creates / updates:
#   * environments dev (branch master|main), staging (branch stage), prod (tags v*, required
#     reviewers = REVIEWERS, 5-minute wait timer off) — deploy secrets/vars are added per
#     environment afterwards (RUNBOOK «CI/CD and environments»);
#   * branch `stage` (from the main branch, if missing) protected against force-push and deletion;
#   * repository variable DEPLOY_ENVIRONMENTS ("none": no deploy until servers exist — set it to
#     "dev,staging,prod" when they do) and the `incident` issue label.
# Re-running is safe.
set -euo pipefail
REPO="${REPO:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
MAIN="${MAIN_BRANCH:-master}"
REVIEWERS="${REVIEWERS:-}"

api() { gh api -H "Accept: application/vnd.github+json" "$@"; }

ensure_env() {  # ensure_env NAME REVIEWERS_JSON
  local name="$1" reviewers="$2"
  api -X PUT "repos/${REPO}/environments/${name}" --input - <<JSON >/dev/null
{"reviewers": ${reviewers}, "deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
  echo "environment ${name}: ok"
}

add_policy() {  # add_policy ENV NAME TYPE
  api -X POST "repos/${REPO}/environments/$1/deployment-branch-policies" \
    -f name="$2" -f type="$3" >/dev/null 2>&1 || true   # already there → fine
}

reviewer_json="[]"
if [[ -n "${REVIEWERS}" ]]; then
  items=()
  for login in ${REVIEWERS}; do
    id="$(api "users/${login}" --jq .id)"
    items+=("{\"type\": \"User\", \"id\": ${id}}")
  done
  reviewer_json="[$(IFS=,; echo "${items[*]}")]"
fi

ensure_env dev "[]"
add_policy dev "${MAIN}" branch
add_policy dev main branch
ensure_env staging "[]"
add_policy staging stage branch
ensure_env prod "${reviewer_json}"
add_policy prod "v*" tag
[[ "${reviewer_json}" == "[]" ]] && echo "warning: prod has no required reviewers (set REVIEWERS)"

if ! api "repos/${REPO}/branches/stage" >/dev/null 2>&1; then
  sha="$(api "repos/${REPO}/git/ref/heads/${MAIN}" --jq .object.sha)"
  api -X POST "repos/${REPO}/git/refs" -f ref=refs/heads/stage -f sha="${sha}" >/dev/null
  echo "branch stage created from ${MAIN} (${sha:0:12})"
fi
api -X PUT "repos/${REPO}/branches/stage/protection" --input - <<'JSON' >/dev/null
{"required_status_checks": null, "enforce_admins": false, "required_pull_request_reviews": null,
 "restrictions": null, "allow_force_pushes": false, "allow_deletions": false}
JSON
echo "branch stage: no force-push, no deletion"

if ! gh variable list --repo "${REPO}" --json name --jq '.[].name' | grep -qx DEPLOY_ENVIRONMENTS; then
  gh variable set DEPLOY_ENVIRONMENTS --repo "${REPO}" --body "none"  # GitHub rejects empty values
fi
gh label create incident --repo "${REPO}" --color B60205 \
  --description "Production is failing (monitor.yml)" --force >/dev/null
echo "done — next: per-environment vars/secrets (RUNBOOK), then DEPLOY_ENVIRONMENTS=dev,staging,prod"
