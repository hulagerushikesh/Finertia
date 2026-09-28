#!/usr/bin/env bash
# One-time setup: GitHub Actions -> Cloud Run deploys via Workload Identity
# Federation (no long-lived key). Safe to re-run: "already exists" errors on
# create steps are ignored; bindings are idempotent. Run once, by a project
# owner, from a machine with gcloud and gh logged in. Done 28 Sep 2026.
set -euo pipefail

P=momentbacktracking
PN=818037622374
REPO=hulagerushikesh/Finertia
SA=finertia-deployer@$P.iam.gserviceaccount.com
RUNTIME=finertia-api-runtime@$P.iam.gserviceaccount.com
# Cloud Build runs `--source` builds as the default compute SA; whoever submits
# the build must be able to act as it. Without this the deploy step fails with
# "default service account is missing required IAM permissions".
BUILD_SA=$PN-compute@developer.gserviceaccount.com

echo "== 1. APIs"
gcloud services enable iamcredentials.googleapis.com sts.googleapis.com --project $P

echo "== 2. Deployer service account"
gcloud iam service-accounts create finertia-deployer --project $P \
  --display-name "GitHub Actions deployer (Cloud Run)" || true

echo "== 3. Roles for 'gcloud run deploy --source'"
for r in roles/run.admin roles/cloudbuild.builds.editor roles/artifactregistry.writer \
         roles/storage.admin roles/serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding $P --member "serviceAccount:$SA" \
    --role $r --condition=None --quiet --format=none
  echo "  granted $r"
done
# actAs only on the runtime SA, not project-wide
gcloud iam service-accounts add-iam-policy-binding $RUNTIME --project $P \
  --member "serviceAccount:$SA" --role roles/iam.serviceAccountUser --format=none
echo "  granted actAs on $RUNTIME"
gcloud iam service-accounts add-iam-policy-binding $BUILD_SA --project $P \
  --member "serviceAccount:$SA" --role roles/iam.serviceAccountUser --format=none
echo "  granted actAs on $BUILD_SA (Cloud Build)"

echo "== 4. Workload Identity pool + GitHub OIDC provider (this repo, main only)"
gcloud iam workload-identity-pools create github --project $P --location global \
  --display-name "GitHub Actions" || true
gcloud iam workload-identity-pools providers create-oidc github --project $P \
  --location global --workload-identity-pool github \
  --display-name "GitHub OIDC" \
  --issuer-uri "https://token.actions.githubusercontent.com" \
  --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition "assertion.repository == '$REPO' && assertion.ref == 'refs/heads/main'" || true

gcloud iam service-accounts add-iam-policy-binding $SA --project $P \
  --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/$PN/locations/global/workloadIdentityPools/github/attribute.repository/$REPO" \
  --format=none
echo "  bound workloadIdentityUser for $REPO"

echo "== 5. GitHub repo secrets"
gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER -R $REPO \
  --body "projects/$PN/locations/global/workloadIdentityPools/github/providers/github"
gh secret set GCP_SERVICE_ACCOUNT -R $REPO --body "$SA"

echo "== done"
gh secret list -R $REPO
