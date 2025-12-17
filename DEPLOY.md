# Stock Analyzer - Google Cloud Run Deployment Guide

## Prerequisites

1. **Google Cloud Account** - Sign up at [cloud.google.com](https://cloud.google.com)
2. **Google Cloud CLI (gcloud)** - [Install here](https://cloud.google.com/sdk/docs/install)
3. **Docker** (optional, for local testing)

---

## One-Time Setup

### 1. Login to Google Cloud
```bash
gcloud auth login
```

### 2. Create a New Project (or use existing)
```bash
# Create new project
gcloud projects create stock-analyzer-app --name="Stock Analyzer"

# Set as default project
gcloud config set project stock-analyzer-app
```

### 3. Enable Required APIs
```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### 4. Set Default Region
```bash
gcloud config set run/region us-central1
```

---

## Deploy to Cloud Run

### Option A: Direct Deploy (Easiest)
This builds and deploys in one command:

```bash
gcloud run deploy stock-analyzer \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 300
```

### Option B: Build & Deploy Separately

1. **Build the container:**
```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/stock-analyzer
```

2. **Deploy to Cloud Run:**
```bash
gcloud run deploy stock-analyzer \
  --image gcr.io/YOUR_PROJECT_ID/stock-analyzer \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 300
```

---

## After Deployment

You'll get a URL like:
```
https://stock-analyzer-xxxxxxxxxx-uc.a.run.app
```

This is your live Stock Analyzer app! 🚀

---

## Useful Commands

### View Logs
```bash
gcloud run logs read stock-analyzer --region us-central1
```

### Update Deployment
```bash
gcloud run deploy stock-analyzer --source . --region us-central1
```

### Delete Service (if needed)
```bash
gcloud run services delete stock-analyzer --region us-central1
```

---

## Cost Estimate

Cloud Run Free Tier includes:
- 2 million requests/month
- 180,000 vCPU-seconds/month  
- 360,000 GB-seconds memory/month

**For personal use, this should be completely FREE!**

---

## Persistent Watchlist Setup (Optional)

By default, the watchlist is read-only from `config.json`. To enable add/remove from UI:

### Create a GCS Bucket

```bash
# Create bucket (use your project ID)
gsutil mb gs://YOUR_PROJECT_ID-watchlist

# Allow Cloud Run service account access
gsutil iam ch serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com:objectAdmin gs://YOUR_PROJECT_ID-watchlist
```

### Deploy with GCS Bucket

```bash
gcloud run deploy stock-analyzer \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 300 \
  --set-env-vars "GCS_BUCKET=YOUR_PROJECT_ID-watchlist"
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GCS_BUCKET` | No | GCS bucket for watchlist. If not set, uses local config.json (read-only) |

**Cost**: Free within 5GB Cloud Storage limit.

---

## Local Testing with Docker

```bash
# Build locally
docker build -t stock-analyzer .

# Run locally
docker run -p 8080:8080 stock-analyzer

# Open http://localhost:8080
```
