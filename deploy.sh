#!/bin/bash

# Wind-Damage Photo Aggregator Deployment Script
# This script automates the deployment process for the Lambda function

echo "🚀 Starting deployment process..."

# Step 1: Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r src/requirements.txt -t src/

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Step 2: Create Lambda deployment package
echo "📦 Creating Lambda deployment package..."
cd src
zip -r ../lambda.zip .
cd ..

if [ $? -ne 0 ]; then
    echo "❌ Failed to create zip file"
    exit 1
fi

echo "✅ Lambda package created successfully"

# Step 3: Initialize Terraform
echo "🔧 Initializing Terraform..."
cd iac
terraform init

if [ $? -ne 0 ]; then
    echo "❌ Terraform initialization failed"
    exit 1
fi

# Step 4: Deploy with Terraform
echo "🌍 Deploying with Terraform..."
terraform apply -auto-approve

if [ $? -ne 0 ]; then
    echo "❌ Terraform deployment failed"
    exit 1
fi

echo "✅ Deployment completed successfully!"
echo "🎉 Your Lambda function is now deployed and ready to use!" 