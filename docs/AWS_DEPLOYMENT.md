# VoxAssist Frontline AWS Deployment

This deploys the current unfinished app safely enough for demos, with HTTPS for microphone access and WSS for the live session socket. Later code updates only need a backend pull/restart and a new frontend build upload.

## Target Architecture

```text
yourdomain.com      -> CloudFront -> S3 static frontend
api.yourdomain.com  -> EC2 Nginx 443 -> FastAPI on 127.0.0.1:8000
MongoDB Atlas M0    -> Backend persistence
```

Use two hostnames:

- `yourdomain.com`, `www.yourdomain.com`, or `app.yourdomain.com` for React.
- `api.yourdomain.com` for FastAPI and WebSockets.

## 1. Create MongoDB Atlas

Create a free M0 cluster, a user such as `voxassist`, and copy the driver URI:

```text
mongodb+srv://voxassist:PASSWORD@cluster0.xxxxx.mongodb.net/voxassist?retryWrites=true&w=majority
```

For a fast demo deployment you can allow `0.0.0.0/0` in Atlas Network Access. Tighten this later.

## 2. Launch EC2

Use Amazon Linux 2023, `t2.micro` or `t3.micro`, 8 GB gp3, and this inbound security group:

| Type | Port | Source | Purpose |
| --- | ---: | --- | --- |
| SSH | 22 | My IP | Admin access |
| HTTP | 80 | 0.0.0.0/0 | Certbot challenge and redirect |
| HTTPS | 443 | 0.0.0.0/0 | API and WSS traffic |

Do not expose port `8000` publicly. Attach an Elastic IP before creating DNS records.

Create DNS:

```text
A    api    YOUR_EC2_ELASTIC_IP
```

Verify:

```bash
nslookup api.yourdomain.com
```

## 3. Prepare EC2

SSH in:

```bash
chmod 400 voxassist-key.pem
ssh -i voxassist-key.pem ec2-user@YOUR_EC2_IP
```

Install runtime dependencies:

```bash
sudo dnf update -y
sudo dnf install python3.11 python3.11-pip git nginx -y
sudo pip3.11 install virtualenv
sudo dnf install python3-certbot-nginx -y || pip3.11 install certbot certbot-nginx --user
```

Get the app onto the server. Preferred after you create a repository:

```bash
cd /home/ec2-user
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git voxassist
cd voxassist
```

If the repo is not pushed yet, copy the folder from your laptop:

```bash
rsync -av --exclude frontend/node_modules --exclude frontend/dist --exclude .venv --exclude .chroma \
  ./ ec2-user@YOUR_EC2_IP:/home/ec2-user/voxassist/
```

## 4. Backend Environment

Create `/home/ec2-user/voxassist/backend/.env`:

```bash
SARVAM_API_KEY=your_sarvam_api_key_here
GEMINI_API_KEY=
MONGODB_URI=mongodb+srv://voxassist:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/voxassist?retryWrites=true&w=majority
MONGODB_DB=voxassist
CHROMA_PERSIST_DIR=/home/ec2-user/voxassist/backend/.chroma
KB_DATA_DIR=/home/ec2-user/voxassist/backend/data/kb
DEFAULT_BRANCH_ID=default
RAG_TOP_K=5
RAG_MIN_CONFIDENCE=0.18
RAG_USE_LLM=true
AI_FAST_MODE=true
JWT_SECRET=replace-with-a-long-random-secret-minimum-32-chars
ALLOWED_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com","https://app.yourdomain.com"]
DEVANAGARI_FONT_PATH=
```

Install and smoke-test the backend:

```bash
cd /home/ec2-user/voxassist
python3.11 -m virtualenv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

From another SSH shell:

```bash
curl http://127.0.0.1:8000/health
```

Stop the manual server after the health check.

## 5. Nginx and SSL

Copy the temporary HTTP config:

```bash
sudo cp /home/ec2-user/voxassist/deploy/nginx/voxassist-http-first.conf /etc/nginx/conf.d/voxassist.conf
sudo sed -i 's/api.yourdomain.com/api.ACTUAL_DOMAIN.com/g' /etc/nginx/conf.d/voxassist.conf
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl start nginx
```

Get the certificate:

```bash
sudo certbot --nginx -d api.ACTUAL_DOMAIN.com --non-interactive --agree-tos -m YOUR_EMAIL
```

If `sudo certbot` is unavailable:

```bash
~/.local/bin/certbot --nginx -d api.ACTUAL_DOMAIN.com --non-interactive --agree-tos -m YOUR_EMAIL
```

Then install the production WSS config:

```bash
sudo cp /home/ec2-user/voxassist/deploy/nginx/voxassist.conf /etc/nginx/conf.d/voxassist.conf
sudo sed -i 's/api.yourdomain.com/api.ACTUAL_DOMAIN.com/g' /etc/nginx/conf.d/voxassist.conf
sudo nginx -t
sudo systemctl reload nginx
```

## 6. Run Backend with systemd

```bash
sudo cp /home/ec2-user/voxassist/deploy/systemd/voxassist.service /etc/systemd/system/voxassist.service
sudo systemctl daemon-reload
sudo systemctl enable voxassist
sudo systemctl start voxassist
sudo systemctl status voxassist
curl https://api.ACTUAL_DOMAIN.com/health
```

Logs:

```bash
sudo journalctl -u voxassist -n 80 --no-pager
sudo journalctl -u nginx -n 80 --no-pager
```

## 7. Frontend Build

On your laptop:

```bash
cd frontend
cp .env.production.example .env.production
```

Edit `.env.production`:

```bash
VITE_VOXASSIST_WS_URL=wss://api.ACTUAL_DOMAIN.com/ws/session/demo-session
VITE_VOXASSIST_API_URL=https://api.ACTUAL_DOMAIN.com
VITE_API_BASE=https://api.ACTUAL_DOMAIN.com
```

Build:

```bash
npm install
npm run build
```

## 8. S3 and CloudFront

Create an S3 bucket for the static frontend. If using the simple S3 website hosting path:

```bash
aws s3 mb s3://voxassist-app-YOUR_NAME --region YOUR_REGION
aws s3 website s3://voxassist-app-YOUR_NAME --index-document index.html --error-document index.html
aws s3api put-public-access-block --bucket voxassist-app-YOUR_NAME --public-access-block-configuration "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
cp deploy/aws/bucket-policy.template.json /tmp/voxassist-bucket-policy.json
sed -i.bak 's/REPLACE_WITH_BUCKET_NAME/voxassist-app-YOUR_NAME/g' /tmp/voxassist-bucket-policy.json
aws s3api put-bucket-policy --bucket voxassist-app-YOUR_NAME --policy file:///tmp/voxassist-bucket-policy.json
aws s3 sync frontend/dist/ s3://voxassist-app-YOUR_NAME/ --delete
```

`deploy/aws/bucket-policy.template.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicRead",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::voxassist-app-YOUR_NAME/*"
  }]
}
```

Create a CloudFront distribution:

- Origin: the S3 website endpoint, such as `voxassist-app-YOUR_NAME.s3-website-REGION.amazonaws.com`.
- Origin protocol: HTTP only.
- Viewer protocol policy: Redirect HTTP to HTTPS.
- Default root object: `index.html`.
- Custom error responses: `403 -> /index.html -> 200` and `404 -> /index.html -> 200`.
- Alternate domain names: your frontend hostnames.
- Certificate: request or select an ACM certificate in `us-east-1` for the frontend domain.

DNS:

```text
CNAME  www  YOUR_DISTRIBUTION.cloudfront.net
A      @    ALIAS/ANAME to YOUR_DISTRIBUTION.cloudfront.net
```

If your DNS provider does not support root ALIAS/ANAME, use `app.yourdomain.com` as a CNAME.

## 9. Seed Demo Data

On EC2:

```bash
cd /home/ec2-user/voxassist
source .venv/bin/activate
python deploy/scripts/seed_demo_data.py
```

## 10. Verify

```bash
curl https://api.ACTUAL_DOMAIN.com/health
curl -X POST https://api.ACTUAL_DOMAIN.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"staff1","password":"staff123"}'
```

Install `wscat` where Node is available:

```bash
npm install -g wscat
TOKEN=$(curl -s -X POST https://api.ACTUAL_DOMAIN.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"staff1","password":"staff123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
wscat -c "wss://api.ACTUAL_DOMAIN.com/ws/session/test-verify?token=$TOKEN"
```

Browser microphone test on the HTTPS frontend:

```js
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(() => console.log("MIC WORKS"))
  .catch(console.error)
```

## Redeploy Later

Backend:

```bash
cd /home/ec2-user/voxassist
git pull
source .venv/bin/activate
pip install -r backend/requirements.txt
sudo systemctl restart voxassist
```

Frontend:

```bash
npm --prefix frontend run build
aws s3 sync frontend/dist/ s3://voxassist-app-YOUR_NAME/ --delete
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```
