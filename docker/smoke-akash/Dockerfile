# Minimal HTTP service for Akash smoke deploys: GET /health returns 200.
# Build/push before deploy (providers pull public registry):
#   docker build -t YOUR_DOCKERHUB_USER/xion-akash-smoke:minimal docker/smoke-akash
#   docker push YOUR_DOCKERHUB_USER/xion-akash-smoke:minimal
# Then set the same image ref in infra/akash/relay-smoke-minimal.yaml.
FROM nginx:alpine
COPY default.conf /etc/nginx/conf.d/default.conf
