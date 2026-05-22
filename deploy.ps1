# Deploy mharetech.co.za — push to GitHub then apply on the live server
param([string]$Message = "")

# 1. Push to GitHub
Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
git push origin master
if (-not $?) { Write-Host "Git push failed." -ForegroundColor Red; exit 1 }

# 2. Deploy on the Azure VM
Write-Host "Deploying to mharetech.co.za..." -ForegroundColor Cyan
ssh azureuser@20.164.200.242 @'
  set -e
  cd /home/azureuser/mharetech
  git pull
  source .venv/bin/activate
  python manage.py collectstatic --noinput
  sudo systemctl restart mharetech
  echo "Deploy complete."
'@
if (-not $?) { Write-Host "Deploy failed." -ForegroundColor Red; exit 1 }

Write-Host "Live at https://mharetech.co.za" -ForegroundColor Green
