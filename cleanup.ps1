# Wind-Damage Photo Aggregator Cleanup Script (PowerShell)
# This script completely removes all AWS resources and local files

Write-Host "🧹 Starting complete cleanup process..." -ForegroundColor Yellow

# Step 1: Destroy Terraform resources
Write-Host "🗑️  Destroying AWS resources..." -ForegroundColor Yellow
Set-Location iac
terraform destroy -auto-approve

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Terraform destroy failed" -ForegroundColor Red
    exit 1
}

# Step 2: Clean up local files
Write-Host "🧹 Cleaning up local files..." -ForegroundColor Yellow
Set-Location ..
Remove-Item lambda.zip -ErrorAction SilentlyContinue
Remove-Item teardown.ps1 -ErrorAction SilentlyContinue
Remove-Item teardown.sh -ErrorAction SilentlyContinue

# Step 3: Verify cleanup
Write-Host "✅ Verifying cleanup..." -ForegroundColor Yellow
try {
    aws lambda get-function --function-name wind-damage-aggregator 2>$null
    Write-Host "⚠️  Lambda function may still exist" -ForegroundColor Yellow
} catch {
    Write-Host "✅ Lambda function successfully deleted" -ForegroundColor Green
}

Write-Host "🎉 Cleanup completed successfully!" -ForegroundColor Green 