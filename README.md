# Wind-Damage Photo Aggregator

A serverless AWS Lambda application that analyzes wind damage photos using AWS Rekognition and provides comprehensive damage assessment reports.

## Overview

This application processes multiple images of wind damage, analyzes them using AWS Rekognition for object detection, and generates a detailed report with damage severity, confirmed areas, and data gaps.

## Features

- **Batch Image Processing**: Ingests up to 100 public JPEG image URLs per claim
- **AI-Powered Analysis**: Uses AWS Rekognition for intelligent object and damage detection
- **Multi-Area Assessment**: Analyzes damage across roof, siding, garage, windows, doors, and fences
- **Severity Classification**: Categorizes damage into 5 levels (0-4) based on confidence scores
- **Quality Filtering**: Automatically discards low-quality or unrelated images
- **Damage Confirmation**: Confirms damage when multiple photos show consistent evidence
- **Data Gap Detection**: Identifies missing photo coverage for comprehensive assessment
- **Real-time Processing**: Serverless architecture with concurrent image processing
- **Structured Output**: Returns detailed JSON reports with confidence scores and metadata

## Assumptions

- **Image Analysis**: Uses AWS Rekognition and simple heuristics for damage detection
- **Storage**: No persistent storage; Lambda /tmp is used for temporary files if needed
- **Image Access**: All image URLs must be public and accessible from AWS Lambda
- **Authentication**: No authentication required for the API (can be added for production)
- **Image Format**: Optimized for JPEG images, but supports other common formats
- **Concurrent Processing**: Uses ThreadPoolExecutor for parallel image processing
- **Error Handling**: Graceful degradation with detailed error reporting
- **Scalability**: Designed for demonstration but can be extended for production use

## Project Structure

```
WAMY/
├── src/                    # Lambda function source code
│   ├── lambda_function.py  # Main Lambda handler
│   └── requirements.txt    # Python dependencies
├── iac/                    # Infrastructure as Code
│   └── main.tf            # Terraform configuration
├── test/                   # Test files
│   ├── sample_request.json # Example API request
│   └── sample_response.json # Example API response
├── deploy.ps1             # Windows deployment script
├── deploy.sh              # Linux/Mac deployment script
├── cleanup.ps1            # Windows cleanup script
├── cleanup.sh             # Linux/Mac cleanup script
├── lambda.zip             # Lambda deployment package (generated)
└── README.md              # This documentation
```

## API Response Structure & Calculations

### Request Format
```json
{
  "claim_id": "CLM-2025-00123",
  "loss_type": "wind",
  "images": [
    "https://example.com/photo1.jpg",
    "https://example.com/photo2.jpg"
  ]
}
```

### Response Format
```json
{
  "claim_id": "CLM-2025-00123",
  "source_images": {
    "total": 30,
    "analyzed": 25,
    "discarded_low_quality": 5,
    "clusters": 3
  },
  "overall_damage_severity": 2.8,
  "areas": [
    {
      "area": "roof",
      "damage_confirmed": true,
      "primary_peril": "wind",
      "count": 8,
      "avg_severity": 3.2,
      "representative_images": ["url1", "url2"],
      "notes": "Shingle damage detected"
    }
  ],
  "data_gaps": ["No attic photos"],
  "confidence": 0.87,
  "generated_at": "2025-06-21T16:31:08.707324Z"
}
```

## Detailed Response Field Calculations

### 1. `source_images` Object

#### `total`
- **Calculation**: `len(images)` - Total number of images in the request
- **Example**: If request contains 30 images, `total: 30`

#### `analyzed`
- **Calculation**: Count of images that passed quality checks and were processed
- **Logic**: Images with `status == "ok"` from the analysis
- **Example**: If 25 out of 30 images were successfully analyzed, `analyzed: 25`

#### `discarded_low_quality`
- **Calculation**: Count of images that failed quality checks
- **Logic**: Images with `status != "ok"` (includes "unrelated", "error")
- **Reasons for discard**:
  - No wind damage keywords detected (`wind`, `damage`, `debris`, `shingle`)
  - No area keywords detected (`roof`, `siding`, `garage`, `window`, `door`, `fence`)
  - Image download failure
  - AWS Rekognition processing error
- **Example**: If 5 images were discarded, `discarded_low_quality: 5`

#### `clusters`
- **Calculation**: `len(area_counts)` - Number of unique damage areas detected
- **Logic**: Count of distinct areas (roof, siding, garage, etc.) where damage was found
- **Example**: If damage was found on roof, siding, and garage, `clusters: 3`

### 2. `overall_damage_severity`

#### Calculation Formula
```
overall_damage_severity = sum(severity × quality) / sum(quality)
```

#### Detailed Steps
1. **Filter images**: Only include images with `has_wind_damage == true` and `severity > 0`
2. **Calculate weighted sum**: `sum(severity × quality_score)` for all valid images
3. **Calculate total weight**: `sum(quality_score)` for all valid images
4. **Final calculation**: `weighted_sum / total_weight`
5. **Round to 2 decimal places**

#### Example
- Image 1: severity=3, quality=100 → weight=300
- Image 2: severity=2, quality=90 → weight=180
- Image 3: severity=4, quality=95 → weight=380
- **Result**: `(300 + 180 + 380) / (100 + 90 + 95) = 860 / 285 = 3.02`

### 3. `areas` Array

Each area object contains damage analysis for a specific building area:

#### `area`
- **Values**: `"roof"`, `"siding"`, `"garage"`, `"window"`, `"door"`, `"fence"`
- **Detection**: Based on AWS Rekognition labels matching area keywords

#### `damage_confirmed`
- **Calculation**: `count(images with severity >= 2) >= 2`
- **Logic**: Damage is confirmed if at least 2 photos of the same area show severity level 2 or higher
- **Severity levels**:
  - 0: No damage
  - 1: Minor damage
  - 2: Moderate damage
  - 3: Significant damage
  - 4: Severe damage

#### `primary_peril`
- **Value**: Always `"wind"` for this application
- **Purpose**: Identifies the type of damage being analyzed

#### `count`
- **Calculation**: Number of images analyzed for this specific area
- **Example**: If 8 roof photos were processed, `count: 8`

#### `avg_severity`
- **Calculation**: `sum(severities) / count` for the specific area
- **Example**: If roof severities were [3, 2, 4, 3, 2, 4, 3, 3], then `avg_severity: 3.0`

#### `representative_images`
- **Selection**: URLs of images with highest quality scores for the area
- **Purpose**: Provides reference images for the damage assessment

#### `notes`
- **Content**: Descriptive text about the damage detected
- **Source**: Generated from AWS Rekognition labels and damage analysis

### 4. `data_gaps` Array

#### Detection Logic
- **Missing areas**: Check if expected areas are not present in `area_counts`
- **Common gaps**:
  - `"No attic photos"` - if `"attic"` not in detected areas
  - `"No interior photos"` - if no interior areas detected
  - `"No structural photos"` - if no structural elements found

#### Purpose
- Identifies areas that should be photographed but weren't
- Helps assess completeness of the damage documentation

### 5. `confidence`

#### Calculation
```python
if analyzed > 0:
    confidence = min(0.95, (analyzed / total) * 0.9 + 0.1)
else:
    confidence = 0.1
```

#### Logic
- **Base confidence**: 10% minimum
- **Quality factor**: Increases based on percentage of successfully analyzed images
- **Maximum**: 95% confidence cap
- **Example**: If 25/30 images analyzed successfully, confidence = min(0.95, (25/30)*0.9 + 0.1) = 0.85

### 6. `generated_at`

#### Format
- **ISO 8601 timestamp** with UTC timezone
- **Example**: `"2025-06-21T16:31:08.707324Z"`

## Severity Calculation Details

### Severity Thresholds
```python
SEVERITY_THRESHOLDS = [0, 60, 75, 85, 92, 100]  # Maps to severity 0-4
```

### Mapping Logic
- **Confidence 0-59**: Severity 0 (No damage)
- **Confidence 60-74**: Severity 1 (Minor damage)
- **Confidence 75-84**: Severity 2 (Moderate damage)
- **Confidence 85-91**: Severity 3 (Significant damage)
- **Confidence 92-100**: Severity 4 (Severe damage)

### Damage Keywords
The system looks for these keywords in AWS Rekognition labels:
- **Wind damage**: `"wind"`, `"damage"`, `"debris"`, `"shingle"`
- **Areas**: `"roof"`, `"siding"`, `"garage"`, `"window"`, `"door"`, `"fence"`

## Step-by-Step Implementation Guide

### Prerequisites

#### 1. Install Required Software

**Windows (PowerShell as Administrator):**
```powershell
# Install Chocolatey package manager
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install required tools
choco install awscli terraform python311 git -y
```

**Manual Installation (Alternative):**
- **AWS CLI**: Download from https://aws.amazon.com/cli/
- **Terraform**: Download from https://www.terraform.io/downloads
- **Python 3.11**: Download from https://www.python.org/downloads/
- **Git**: Download from https://git-scm.com/downloads

#### 2. AWS Account Setup

**Step 1: Create AWS Account**
1. Go to https://aws.amazon.com/
2. Click "Create an AWS Account"
3. Follow registration process (requires credit card for verification)
4. Note: AWS offers free tier for new accounts

**Step 2: Create IAM User**
1. Log into AWS Console
2. Navigate to IAM (Identity and Access Management)
3. Click "Users" → "Create user"
4. Name: `wind-damage-admin`
5. Check "Access key - Programmatic access"
6. Click "Next: Permissions"
7. Click "Attach existing policies directly"
8. Search and select `AdministratorAccess`
9. Click "Next: Tags" → "Next: Review" → "Create user"
10. **IMPORTANT**: Download the CSV file with Access Key ID and Secret Access Key

**Step 3: Configure AWS CLI**
```powershell
aws configure
```
Enter when prompted:
- AWS Access Key ID: [from the CSV file]
- AWS Secret Access Key: [from the CSV file]
- Default region name: `us-east-1`
- Default output format: `json`

### Project Setup

#### 1. Clone/Setup Project
```powershell
# Navigate to your desired directory
cd C:\Your\Project\Path

# Clone or copy project files
# Ensure you have these files:
# - src/lambda_function.py
# - iac/main.tf
# - test/sample_request.json
# - test/sample_response.json
# - requirements.txt
```

#### 2. Install Python Dependencies
```powershell
# Create requirements.txt if not exists
echo "boto3==1.34.0" > src/requirements.txt
echo "requests==2.31.0" >> src/requirements.txt

# Install dependencies
pip install -r src/requirements.txt
```

### Deployment

#### Understanding the Lambda Deployment Package (ZIP Process)

**Why ZIP is Required:**
AWS Lambda requires all code and dependencies to be packaged in a single ZIP file. This is because:
- Lambda runs in an isolated environment without your local Python packages
- Third-party libraries like `requests` and `boto3` are not included in Lambda's runtime
- The ZIP file must contain everything needed to run your function

**What Gets Zipped:**
```
lambda.zip contents:
├── lambda_function.py     # Your main code
├── requirements.txt       # Dependency list
├── requests/             # HTTP library (installed)
├── boto3/               # AWS SDK (installed)
├── botocore/            # AWS SDK core (installed)
├── urllib3/             # HTTP library dependency
├── certifi/             # SSL certificates
├── charset_normalizer/  # Text encoding
├── idna/                # International domain names
├── jmespath/            # JSON query language
├── python_dateutil/     # Date utilities
├── s3transfer/          # S3 transfer utilities
├── six.py               # Python 2/3 compatibility
└── [other dependencies] # Additional installed packages
```

**ZIP Creation Process:**
1. **Install Dependencies**: `pip install -r requirements.txt -t src/`
   - `-t src/` installs packages into the `src/` directory
   - This creates folders like `requests/`, `boto3/`, etc.
2. **Create ZIP**: `zip -r ../lambda.zip .` (from inside `src/`)
   - Includes all files and folders in the ZIP
   - Maintains the directory structure
   - Lambda expects dependencies at the root level

**Important Notes:**
- **File Size**: The ZIP can be large (15MB+) due to dependencies
- **Upload Time**: Large ZIPs take longer to upload to AWS
- **Cold Start**: Larger packages may increase Lambda cold start time
- **Dependencies**: Only include what you actually use to minimize size

#### Option 1: Using Automated Script (Recommended)

**Windows:**
```powershell
.\deploy.ps1
```

**Linux/Mac:**
```bash
./deploy.sh
```

#### Option 2: Manual Deployment

**Step 1: Bundle Dependencies**
```powershell
# Install dependencies to src directory
pip install -r src/requirements.txt -t src/

# Create Lambda deployment package
cd src
zip -r ../lambda.zip .
cd ..
```

**Step 2: Deploy Infrastructure**
```powershell
# Navigate to infrastructure directory
cd iac

# Initialize Terraform
terraform init

# Plan deployment (optional)
terraform plan

# Deploy infrastructure
terraform apply -auto-approve
```

**Expected Output:**
```
Apply complete! Resources: 8 added, 0 changed, 0 destroyed.

Outputs:
api_endpoint = "https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com"
```

### Testing

#### 1. Test with Sample Request

**Using PowerShell:**
```powershell
# Get API endpoint from Terraform output
$apiUrl = "YOUR_API_ENDPOINT_FROM_TERRAFORM_OUTPUT"

# Test with sample request
$headers = @{
    "Content-Type" = "application/json"
}
$body = Get-Content "test/sample_request.json" -Raw

Invoke-RestMethod -Uri "$apiUrl/aggregate" -Method POST -Headers $headers -Body $body
```

**Using curl:**
```bash
curl -X POST "YOUR_API_ENDPOINT_FROM_TERRAFORM_OUTPUT/aggregate" \
  -H "Content-Type: application/json" \
  -d @test/sample_request.json
```

**Using Postman:**
1. Open Postman
2. Create new request
3. Method: POST
4. URL: `YOUR_API_ENDPOINT_FROM_TERRAFORM_OUTPUT/aggregate`
5. Headers: `Content-Type: application/json`
6. Body: Raw JSON (copy from `test/sample_request.json`)

#### 2. Test with Real Images

**Update sample_request.json:**
```json
{
  "claim_id": "CLM-2025-00123",
  "loss_type": "wind",
  "images": [
    "https://your-real-image-url1.jpg",
    "https://your-real-image-url2.jpg"
  ]
}
```

**Important Notes:**
- Images must be publicly accessible URLs
- AWS Lambda must be able to download the images
- Images should contain wind damage for meaningful results

### Monitoring and Troubleshooting

#### 1. View Lambda Logs
1. Go to AWS Console → CloudWatch → Log groups
2. Find `/aws/lambda/wind-damage-aggregator`
3. Click on latest log stream
4. Look for debug messages and error logs

#### 2. Common Issues and Solutions

**"No module named 'requests'" Error:**
- Ensure dependencies are installed: `pip install -r src/requirements.txt -t src/`
- Recreate zip file and redeploy

**All Images Discarded:**
- Check image URLs are accessible
- Verify images contain wind damage keywords
- Review CloudWatch logs for specific reasons

**500 Internal Server Error:**
- Check CloudWatch logs for detailed error messages
- Verify AWS credentials have proper permissions
- Ensure all required AWS services are available

#### 3. Performance Optimization

**Lambda Configuration:**
- **Timeout**: 30 seconds (adjustable in `iac/main.tf`)
- **Memory**: 512 MB (adjustable in `iac/main.tf`)
- **Concurrent executions**: 10 (adjustable in code)

**Image Processing:**
- **Max images per request**: 30 (adjustable in code)
- **Max labels per image**: 20 (AWS Rekognition limit)
- **Min confidence**: 50% (adjustable in code)

### Cleanup

**To remove all AWS resources:**

#### Option 1: Using Automated Script (Recommended)

**Windows:**
```powershell
# Run the cleanup script
.\cleanup.ps1
```

**Linux/Mac:**
```bash
# Make script executable and run
chmod +x cleanup.sh
./cleanup.sh
```

#### Option 2: Manual Teardown

**Step 1: Review Resources to be Destroyed**
```powershell
cd iac
terraform plan -destroy
```

This will show you exactly what resources will be deleted:
- Lambda function
- API Gateway
- IAM roles and policies
- CloudWatch log groups
- Any other AWS resources created by Terraform

**Step 2: Destroy Resources**
```powershell
# Destroy all resources
terraform destroy -auto-approve
```

**Expected Output:**
```
Destroy complete! Resources: 8 destroyed.
```

#### Option 3: Selective Resource Destruction

**Destroy Specific Resources:**
```powershell
# Destroy only the Lambda function
terraform destroy -target=aws_lambda_function.wind_damage_aggregator

# Destroy only the API Gateway
terraform destroy -target=aws_api_gateway_rest_api.wind_damage_api

# Destroy multiple specific resources
terraform destroy -target=aws_lambda_function.wind_damage_aggregator -target=aws_api_gateway_rest_api.wind_damage_api
```

#### Verification Steps

**Step 1: Check AWS Console**
1. Go to AWS Lambda Console - verify function is deleted
2. Go to API Gateway Console - verify API is deleted
3. Go to IAM Console - verify roles are deleted
4. Go to CloudWatch Console - verify log groups are deleted

**Step 2: Verify via AWS CLI**
```powershell
# Check if Lambda function exists
aws lambda get-function --function-name wind-damage-aggregator

# Check if API Gateway exists
aws apigateway get-rest-apis

# Check if IAM role exists
aws iam get-role --role-name wind-damage-lambda-role

# Check if CloudWatch log group exists
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/wind-damage-aggregator"
```

**Step 3: Clean Up Local Files (Optional)**
```powershell
# Remove generated files
Remove-Item lambda.zip -ErrorAction SilentlyContinue
Remove-Item teardown.ps1 -ErrorAction SilentlyContinue
Remove-Item teardown.sh -ErrorAction SilentlyContinue

# Clean up Terraform state (optional)
cd iac
Remove-Item .terraform -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item terraform.tfstate* -ErrorAction SilentlyContinue
```

#### Safety Considerations

**Before Destroying:**
- **Backup Important Data**: Ensure you have backups of any important configurations
- **Check Dependencies**: Verify no other services depend on these resources
- **Review Costs**: Check AWS billing to understand what you're removing
- **Documentation**: Note down any custom configurations for future reference

**After Destroying:**
- **Verify Deletion**: Use AWS Console or CLI to confirm resources are gone
- **Check Billing**: Monitor AWS billing to ensure charges stop
- **Clean Local State**: Remove local Terraform files if no longer needed

#### Troubleshooting Destruction

**If Terraform Destroy Fails:**

**Error: "Resource still has dependencies"**
```powershell
# Force destroy with dependencies
terraform destroy -auto-approve -refresh=false
```

**Error: "Resource not found"**
```powershell
# Remove from state and retry
terraform state rm aws_lambda_function.wind_damage_aggregator
terraform destroy -auto-approve
```

**Error: "Permission denied"**
```powershell
# Verify AWS credentials
aws sts get-caller-identity

# Reconfigure if needed
aws configure
```

**Warning**: This will delete all created resources and cannot be undone.

## Cost Estimation

**AWS Free Tier (first 12 months):**
- Lambda: 1M requests/month free
- API Gateway: 1M requests/month free
- Rekognition: 5K images/month free

**After free tier:**
- Lambda: ~$0.20 per 1M requests
- API Gateway: ~$1.00 per 1M requests
- Rekognition: ~$1.00 per 1K images

## Customization

#### 1. Add New Damage Areas
Edit `AREA_KEYWORDS` in `src/lambda_function.py`:
```python
AREA_KEYWORDS = {
    "roof": ["roof", "shingle", "ridge"],
    "siding": ["siding", "wall", "panel"],
    "garage": ["garage"],
    "window": ["window"],
    "door": ["door"],
    "fence": ["fence"],
    "attic": ["attic", "ceiling"],  # New area
    "foundation": ["foundation", "base"]  # New area
}
```

#### 3. Adjust Damage Confirmation Rules
Modify the confirmation logic in the damage confirmation section:
```python
# Current: 2+ photos with severity >= 2
confirmed = sum(1 for url in area_images[area] if image_severities.get(url, 0) >= 2) >= 2

# Custom: 3+ photos with severity >= 1
confirmed = sum(1 for url in area_images[area] if image_severities.get(url, 0) >= 1) >= 3
```

## Support

For issues or questions:
1. Check AWS Console for error messages
2. Review CloudWatch logs for detailed debugging
3. Verify all prerequisites are installed correctly
4. Ensure AWS credentials have proper permissions
5. Test with known good images first
