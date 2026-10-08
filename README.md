# IS 373 Deployment

Production: https://megan373lab.xyz
QA: https://qa.megan373lab.xyz

## Deployment process

Pushes to qa deploy QA. After checking QA, I merge those changes into main to deploy production. Each environment uses a separate Docker Compose project and container.

GitHub Actions tests the website, validates configuration, builds a Docker image, and checks that the container serves the expected HTML. A failed test or build stops deployment.

The workflow pushes a commit-tagged image to GitHub Container Registry. It connects to my DigitalOcean server as deploy using an SSH key, starts the selected environment, and verifies the page over HTTPS. Credentials are stored in GitHub Actions secrets.

## Test Evidence

Workflow runs: https://github.com/mtm5913/is373-deployment/actions

Image: ghcr.io/mtm5913/is373-deployment, tagged with the full commit SHA.

Successful deployment links and screenshots will be added after verification.

SSH-key login as deploy and sudo access were tested successfully.
Direct root SSH login was rejected with Permission denied (publickey).
Password-only login was also rejected with Permission denied (publickey).

Effective SSH settings:
- permitrootlogin no
- pubkeyauthentication yes
- passwordauthentication no
- kbdinteractiveauthentication no
