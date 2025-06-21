# Wind-Damage Photo Aggregator Deployment Script (PowerShell)
# This script automates the deployment process for the Lambda function

Write-Host "🚀 Starting deployment process..." -ForegroundColor Green

# Step 1: Install dependencies
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
pip install -r src/requirements.txt -t src/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Step 2: Create Lambda deployment package
Write-Host "📦 Creating Lambda deployment package..." -ForegroundColor Yellow
Set-Location src
zip -r ../lambda.zip .
Set-Location ..

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to create zip file" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Lambda package created successfully" -ForegroundColor Green

# Step 3: Deploy with Terraform
Write-Host "🌍 Deploying with Terraform..." -ForegroundColor Yellow
Set-Location iac
terraform apply -auto-approve

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Terraform deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
Write-Host "🎉 Your Lambda function is now deployed and ready to use!" -ForegroundColor Green 