#!/bin/bash

# Wind-Damage Photo Aggregator Cleanup Script (Bash)
# This script completely removes all AWS resources and local files

echo "🧹 Starting complete cleanup process..."

# Step 1: Destroy Terraform resources
echo "🗑️  Destroying AWS resources..."
cd iac
terraform destroy -auto-approve

if [ $? -ne 0 ]; then
    echo "❌ Terraform destroy failed"
    exit 1
fi

# Step 2: Clean up local files
echo "🧹 Cleaning up local files..."
cd ..
rm -f lambda.zip
rm -f teardown.ps1
rm -f teardown.sh

# Step 3: Verify cleanup
echo "✅ Verifying cleanup..."
if aws lambda get-function --function-name wind-damage-aggregator 2>/dev/null; then
    echo "⚠️  Lambda function may still exist"
else
    echo "✅ Lambda function successfully deleted"
fi

echo "🎉 Cleanup completed successfully!" 