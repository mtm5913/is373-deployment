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

Successful QA workflow: https://github.com/mtm5913/is373-deployment/actions/runs/37822111536
Successful production workflow: https://github.com/mtm5913/is373-deployment/actions/runs/37822315094

SSH-key login as deploy and sudo access were tested successfully.
Direct root SSH login was rejected with Permission denied (publickey).
Password-only login was also rejected with Permission denied (publickey).

Effective SSH settings:
- permitrootlogin no
- pubkeyauthentication yes
- passwordauthentication no
- kbdinteractiveauthentication no
<img width="1440" height="900" alt="Screenshot 2026-10-08 at 2 15 52 PM" src="https://github.com/user-attachments/assets/e93d8c2d-dc72-4fc6-8b6f-c5529c8f1e6b" />
<img width="628" height="744" alt="Screenshot 2026-10-08 at 2 12 48 PM" src="https://github.com/user-attachments/assets/4b3691b2-68bd-4672-a135-b38c7166610c" />
<img width="628" height="741" alt="Screenshot 2026-10-08 at 2 11 32 PM" src="https://github.com/user-attachments/assets/1eed3021-60a8-47a3-a84f-e3337a1c8693" />
<img width="625" height="745" alt="Screenshot 2026-10-08 at 2 11 29 PM" src="https://github.com/user-attachments/assets/3afefe45-9a85-42c5-917f-5fb92a18657a" />
<img width="696" height="416" alt="Screenshot 2026-10-08 at 2 31 02 PM" src="https://github.com/user-attachments/assets/e549d68f-9d53-4580-a569-1726ae14cbcd" />
<img width="1440" height="900" alt="Screenshot 2026-10-08 at 2 28 43 PM" src="https://github.com/user-attachments/assets/ccfd3b5f-072f-404d-a3b4-16823c0de73a" />
