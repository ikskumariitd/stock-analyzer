@echo off
echo Deploying Stock Analyzer to Google Cloud Run...
echo Project ID: stock-analyzer-ik2024
echo Region: us-central1

call gcloud run deploy stock-analyzer ^
  --source . ^
  --platform managed ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --timeout 300 ^
  --project stock-analyzer-ik2024

echo.
pause
