#!/usr/bin/env bash
# The automatable half of the release checklist (RELEASE.md). Read-only: it
# looks at GitHub, the live site and the GCP project, and changes nothing.
#
#   scripts/release-check.sh pre    before triggering a backend deploy
#   scripts/release-check.sh post   after it (or after any frontend merge)
#
# Each line is PASS, WARN (read it, decide) or FAIL (do not ship / roll back).
# Exits 1 if anything failed. Needs git, gh, curl and jq; the GCP checks also
# need gcloud signed in to an account that can read the project, and are
# skipped with a WARN without it.

set -uo pipefail

PROJECT=momentbacktracking
REGION=${REGION:-us-central1}   # REGION=asia-south1 to check the pre-B1 service
SERVICE=finertia-api
SITE=https://finertia.hulage.in
REPO=hulagerushikesh/Finertia
TAG=backend-deployed

fails=0
pass() { printf '  \033[32mPASS\033[0m %s\n' "$*"; }
warn() { printf '  \033[33mWARN\033[0m %s\n' "$*"; }
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$*"; fails=$((fails + 1)); }
info() { printf '       %s\n' "$*"; }
section() { printf '\n%s\n' "$*"; }

for tool in git gh curl jq; do
  command -v "$tool" >/dev/null || { echo "needs $tool"; exit 2; }
done
cd "$(git rev-parse --show-toplevel)" || exit 2

have_gcloud() { command -v gcloud >/dev/null && gcloud auth print-access-token >/dev/null 2>&1; }

gapi() { # GET a Google API URL as the signed-in gcloud account
  curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    -H "x-goog-user-project: $PROJECT" "$1"
}

check_ci() { # $1 = sha
  local ci vercel
  ci=$(gh run list -R "$REPO" --workflow ci.yml --commit "$1" --json status,conclusion \
    -q '.[0] | "\(.status) \(.conclusion)"' 2>/dev/null)
  case "$ci" in
    "completed success") pass "CI green on ${1:0:7}" ;;
    completed*) fail "CI on ${1:0:7}: ${ci#completed }" ;;
    "") fail "no CI run found for ${1:0:7}" ;;
    *) warn "CI on ${1:0:7} still running ($ci)" ;;
  esac
  vercel=$(gh api "repos/$REPO/commits/$1/status" \
    -q '[.statuses[] | select(.context == "Vercel")][0].state' 2>/dev/null)
  case "$vercel" in
    success) pass "Vercel built ${1:0:7}" ;;
    pending) warn "Vercel still building ${1:0:7}" ;;
    *) fail "Vercel on ${1:0:7}: ${vercel:-no status}" ;;
  esac
}

check_rules_live() {
  have_gcloud || { warn "gcloud not signed in: live rules and indexes not checked"; return; }
  local ruleset live
  ruleset=$(gapi "https://firebaserules.googleapis.com/v1/projects/$PROJECT/releases/cloud.firestore" | jq -r '.rulesetName // empty')
  live=$(mktemp)
  gapi "https://firebaserules.googleapis.com/v1/$ruleset" | jq -r '.source.files[0].content // empty' >"$live"
  # Whitespace-insensitive: the console reformats nothing, but a trailing
  # blank line is not a difference worth a deploy.
  if [ ! -s "$live" ]; then
    warn "could not read the live Firestore rules"
  elif diff -wB "$live" firestore.rules >/dev/null; then
    pass "live Firestore rules == firestore.rules"
  else
    fail "live Firestore rules differ from firestore.rules — deploy them: firebase deploy --only firestore:rules --project $PROJECT"
    diff -wB "$live" firestore.rules | sed 's/^/         /' | head -20
  fi
  rm -f "$live"

  local want states
  want=$(jq '.indexes | length' firestore.indexes.json)
  states=$(gcloud firestore indexes composite list --project "$PROJECT" --format='value(state)' 2>/dev/null)
  local ready total
  ready=$(grep -c '^READY$' <<<"$states")
  total=$(grep -c . <<<"$states")
  if [ "$ready" = "$want" ] && [ "$total" = "$want" ]; then
    pass "$want/$want composite indexes READY"
  elif [ "$total" -lt "$want" ]; then
    fail "$total composite indexes live, $want in firestore.indexes.json — firebase deploy --only firestore:indexes --project $PROJECT"
  else
    warn "composite indexes: $ready of $total READY ($want in the file) — wait for CREATING to finish"
  fi
}

pre() {
  section "Repository"
  git fetch -q --tags --force origin main 2>/dev/null
  local head deployed
  head=$(git rev-parse origin/main)
  deployed=$(git rev-parse "$TAG^{commit}" 2>/dev/null) || { fail "no $TAG tag"; return; }
  info "main is ${head:0:7}; $TAG is ${deployed:0:7}"
  [ -z "$(git status --porcelain)" ] || warn "working tree not clean (the workflow deploys origin/main, not this checkout)"
  check_ci "$head"

  section "What a backend deploy would ship"
  local log
  log=$(git log --oneline "$deployed..$head" -- backend/)
  if [ -z "$log" ]; then
    pass "backend/ unchanged since ${deployed:0:7}: nothing to deploy"
  else
    echo "$log" | sed 's/^/         /'
    if git diff --quiet "$deployed" "$head" -- backend/requirements.txt; then
      pass "no dependency changes"
    else
      warn "requirements.txt changed — read it:"
      git diff "$deployed" "$head" -- backend/requirements.txt | grep '^[-+][^-+]' | sed 's/^/         /'
    fi
    # New environment variables the code reads. Each one must already be set
    # on the service (or have a safe default) before the deploy. Matches
    # os.environ reads and helpers named *_env("NAME", …), such as _int_env.
    local envs
    envs=$(git diff "$deployed" "$head" -- 'backend/*.py' ':!backend/tests' |
      grep '^+' | grep -oE '(environ(\.get)?[[(]|_env\()"[A-Z0-9_]+"' | grep -oE '"[A-Z0-9_]+"' | tr -d '"' | sort -u)
    if [ -n "$envs" ]; then
      warn "code now reads: $(echo $envs | tr ' ' ',') — set on the service, or safe when unset?"
    else
      pass "no new environment variables read"
    fi
  fi

  section "Firestore"
  check_rules_live

  section "Rollback target"
  if have_gcloud; then
    local serving
    serving=$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" \
      --format='value(status.traffic[0].revisionName)' 2>/dev/null)
    info "serving now: $serving. If the new revision misbehaves:"
    info "gcloud run services update-traffic $SERVICE --region $REGION --project $PROJECT --to-revisions $serving=100"
  else
    warn "gcloud not signed in: note the serving revision from the Cloud Run console before deploying"
  fi
}

http() { # $1 = url, extra curl args after; prints "code seconds"
  local url=$1; shift
  curl -s -o /dev/null -w '%{http_code} %{time_total}' --max-time 30 "$@" "$url"
}

post() {
  section "Backend"
  git fetch -q --tags --force origin 2>/dev/null
  local deployed health code body commit
  deployed=$(git rev-parse "$TAG^{commit}" 2>/dev/null)
  # Through the site, so Vercel's /api rewrite is checked on the way.
  body=$(curl -s --max-time 30 -w '\n%{http_code} %{time_total}' "$SITE/api/health")
  code=$(tail -n1 <<<"$body")
  health=$(head -n1 <<<"$body")
  if [ "${code%% *}" = "200" ]; then
    pass "/api/health 200 in ${code#* }s (over 3 s means a cold start; run it again)"
  else
    fail "/api/health returned ${code%% *}"
  fi
  commit=$(jq -r '.commit // empty' <<<"$health" 2>/dev/null)
  if [ -z "$commit" ]; then
    warn "/api/health does not name its commit (revision deployed before GIT_SHA was passed)"
  elif [ "$commit" = "$deployed" ]; then
    pass "serving ${commit:0:7} == $TAG ($(jq -r '.revision // "?"' <<<"$health"))"
  else
    fail "serving ${commit:0:7} but $TAG is ${deployed:0:7}"
  fi

  for path in /api/plans /api/strategies; do
    code=$(http "$SITE$path")
    [ "${code%% *}" = 200 ] && pass "$path 200" || fail "$path returned ${code%% *}"
  done
  # Auth still enforced: an admin route without a token must be refused.
  code=$(http "$SITE/api/admin/stats")
  [ "${code%% *}" = 401 ] && pass "/api/admin/stats without a token → 401" || fail "/api/admin/stats without a token → ${code%% *}"
  # ALLOWED_ORIGINS survives deploys only because deploy.yml never passes it.
  # If it were blanked, the browser would block every API call from the site.
  local allow
  allow=$(curl -s -D - -o /dev/null -X OPTIONS --max-time 30 \
    -H "Origin: $SITE" -H "Access-Control-Request-Method: POST" \
    "$SITE/api/backtest" |
    tr -d '\r' | awk -F': ' 'tolower($1) == "access-control-allow-origin" {print $2}')
  [ "$allow" = "$SITE" ] && pass "CORS allows $SITE" || fail "CORS preflight from $SITE got allow-origin '${allow:-none}'"

  section "Frontend"
  check_ci "$(git rev-parse origin/main)"
  for path in / /demo /pricing /writeup /docs /robots.txt /sitemap.xml; do
    code=$(http "$SITE$path")
    [ "${code%% *}" = 200 ] && pass "$path 200" || fail "$path returned ${code%% *}"
  done

  section "Firestore"
  check_rules_live

  if have_gcloud; then
    section "Cloud Run"
    local traffic
    traffic=$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" \
      --format=json 2>/dev/null | jq -r '.status.traffic | map("\(.revisionName)=\(.percent)%") | join(", ")')
    info "traffic: $traffic"
    local errors
    errors=$(gcloud logging read \
      "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE AND severity>=ERROR" \
      --project "$PROJECT" --freshness 30m --limit 20 --format='value(timestamp)' 2>/dev/null | grep -c .)
    [ "$errors" = 0 ] && pass "no ERROR log lines in the last 30 min" || warn "$errors ERROR log lines in the last 30 min — read them before calling it done"
  fi
}

case "${1:-}" in
  pre) pre ;;
  post) post ;;
  *) echo "usage: $0 pre|post"; exit 2 ;;
esac

echo
if [ "$fails" -gt 0 ]; then
  echo "$fails check(s) failed."
  exit 1
fi
echo "Automated checks passed. Now the by-hand ones in RELEASE.md."
