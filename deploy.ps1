<#
.SYNOPSIS
    Build and deploy Orientation Mali to AWS Lambda.
    
.DESCRIPTION
    This script packages the application for Lambda (Linux x86_64),
    uploads to S3, and deploys via CloudFormation.
    
.NOTES
    Requires: AWS CLI configured with appropriate permissions.
    Run from the project root directory.
#>

$ErrorActionPreference = "Stop"

$STACK_NAME = "orientation-mali"
$REGION = "us-east-1"
$BUILD_DIR = ".build"
$PACKAGE_DIR = "$BUILD_DIR\package"

Write-Host "=== Orientation Mali - Deployment ===" -ForegroundColor Cyan

# Step 1: Clean previous build
Write-Host "`n[1/5] Cleaning previous build..." -ForegroundColor Yellow
if (Test-Path $BUILD_DIR) { Remove-Item -Recurse -Force $BUILD_DIR }
New-Item -ItemType Directory -Path $PACKAGE_DIR -Force | Out-Null

# Step 2: Install dependencies for Linux target
Write-Host "[2/5] Installing dependencies for Lambda (linux/x86_64)..." -ForegroundColor Yellow
pip install `
    --target "$PACKAGE_DIR" `
    --platform manylinux2014_x86_64 `
    --implementation cp `
    --python-version 3.12 `
    --only-binary=:all: `
    --upgrade `
    -r requirements.txt 2>&1 | Out-Null

# Some packages don't have pre-built wheels for linux, install them without platform constraint
# (pure Python packages work on any platform)
pip install `
    --target "$PACKAGE_DIR" `
    --upgrade `
    --no-deps `
    strands-agents strands-agents-bedrock mangum 2>&1 | Out-Null

# Step 3: Copy application code
Write-Host "[3/5] Copying application code..." -ForegroundColor Yellow
Copy-Item -Recurse "src" "$PACKAGE_DIR\src"
Copy-Item "handler.py" "$PACKAGE_DIR\handler.py"

# Step 4: Create zip package
Write-Host "[4/5] Creating deployment package..." -ForegroundColor Yellow
$zipPath = "$BUILD_DIR\lambda-package.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }
Compress-Archive -Path "$PACKAGE_DIR\*" -DestinationPath $zipPath -Force

$sizeMB = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Host "   Package size: ${sizeMB} MB" -ForegroundColor Gray

# Step 5: Deploy with SAM/CloudFormation
Write-Host "[5/5] Deploying to AWS ($REGION)..." -ForegroundColor Yellow

# Create S3 bucket for deployment artifacts if it doesn't exist
$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
$S3_BUCKET = "orientation-mali-deploy-$ACCOUNT_ID"

$bucketExists = aws s3api head-bucket --bucket $S3_BUCKET 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "   Creating S3 bucket: $S3_BUCKET" -ForegroundColor Gray
    aws s3api create-bucket --bucket $S3_BUCKET --region $REGION
}

# Upload the package
$S3_KEY = "lambda-package.zip"
Write-Host "   Uploading package to s3://$S3_BUCKET/$S3_KEY" -ForegroundColor Gray
aws s3 cp $zipPath "s3://$S3_BUCKET/$S3_KEY" --region $REGION

# Deploy CloudFormation stack
Write-Host "   Deploying CloudFormation stack: $STACK_NAME" -ForegroundColor Gray
aws cloudformation deploy `
    --template-file template-cf.yaml `
    --stack-name $STACK_NAME `
    --parameter-overrides `
        S3Bucket=$S3_BUCKET `
        S3Key=$S3_KEY `
    --capabilities CAPABILITY_IAM `
    --region $REGION `
    --no-fail-on-empty-changeset

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== Deployment successful! ===" -ForegroundColor Green
    
    # Get the API URL
    $apiUrl = aws cloudformation describe-stacks `
        --stack-name $STACK_NAME `
        --query "Stacks[0].Outputs[?OutputKey=='OrientationMaliApi'].OutputValue" `
        --output text `
        --region $REGION
    
    Write-Host "Application URL: $apiUrl" -ForegroundColor Cyan
} else {
    Write-Host "`n=== Deployment failed ===" -ForegroundColor Red
    exit 1
}
