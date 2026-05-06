param(
    [ValidateSet("full", "base")]
    [string]$Mode = "full"
)

<#
.SYNOPSIS
    Build and deploy Orientation Mali to AWS Lambda.

.DESCRIPTION
    This script packages the application for Lambda (Linux x86_64),
    uploads to S3, and deploys via CloudFormation.

    Use -Mode to control which resources are deployed:
      - "full"  (default): Deploys all resources including custom domain (ACM certificate,
                API Gateway custom domain, API mapping, Route 53 DNS record).
      - "base": Deploys only base infrastructure (Lambda, API Gateway, DynamoDB) without
                custom domain resources. Useful to avoid ACM certificate validation delays.

    Deployment Phases:
      1. Clean      - Remove previous build artifacts
      2. Package    - Install dependencies for Lambda target platform
      3. Prune      - Remove unnecessary files (boto3, __pycache__, tests, etc.)
      4. Zip        - Create deployment package and report size
      5. Check Stack - Detect failed stack states and handle recovery
      6. Upload     - Push zip to S3 with content-hash key
      7. Deploy     - Run CloudFormation deploy with appropriate parameters
      8. Validate   - Health check API Gateway and custom domain endpoints

    Exit Codes:
      0 - Success (deployment and health checks passed)
      1 - Packaging failure (pip install, zip creation, or S3 upload failed)
      2 - Stack state unrecoverable (stack in failed/in-progress state, user declined recovery)
      3 - CloudFormation deployment failure
      4 - Health check warning (deployment succeeded but endpoint verification failed)

    ACM Certificate Timeout:
      CloudFormation's default resource creation timeout is 60 minutes, which is sufficient
      for ACM DNS validation (typically completes in 5-30 minutes). The template uses
      DomainValidationOptions with HostedZoneId, which triggers automatic DNS record creation
      by CloudFormation - no manual intervention is needed. If validation fails, CloudFormation
      rolls back automatically and the script reports exit code 3.

.PARAMETER Mode
    Deployment mode. "full" deploys all resources including custom domain.
    "base" skips custom domain resources. Defaults to "full".

.EXAMPLE
    .\deploy.ps1
    # Full deployment with custom domain

.EXAMPLE
    .\deploy.ps1 -Mode base
    # Base infrastructure only, no custom domain

.NOTES
    Requires: AWS CLI configured with appropriate permissions.
    Run from the project root directory.
#>

$ErrorActionPreference = "Stop"

# Set EnableCustomDomain based on deployment mode
$EnableCustomDomain = if ($Mode -eq "full") { "true" } else { "false" }

$STACK_NAME = "orientation-mali"
$REGION = "us-east-1"
$BUILD_DIR = ".build"
$PACKAGE_DIR = "$BUILD_DIR\package"

Write-Host "=== Orientation Mali - Deployment ===" -ForegroundColor Cyan
Write-Host "   Mode: $Mode (EnableCustomDomain=$EnableCustomDomain)" -ForegroundColor Gray

# =============================================================================
# Step 1: Clean previous build
# =============================================================================
Write-Host "`n[1/8] Cleaning previous build..." -ForegroundColor Yellow
if (Test-Path $BUILD_DIR) { Remove-Item -Recurse -Force $BUILD_DIR }
New-Item -ItemType Directory -Path $PACKAGE_DIR -Force | Out-Null

# =============================================================================
# Step 2: Package - Install dependencies for Linux target
# =============================================================================
Write-Host "[2/8] Installing dependencies for Lambda (linux/x86_64)..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
pip install --target "$PACKAGE_DIR" --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 --only-binary=:all: --upgrade -r requirements.txt 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "   ERROR: pip install (platform-specific) failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit 1
}

# Some packages don't have pre-built wheels for linux, install them without platform constraint
# (pure Python packages work on any platform)
pip install --target "$PACKAGE_DIR" --upgrade --no-deps strands-agents strands-agents-bedrock mangum 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "   ERROR: pip install (pure Python packages) failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit 1
}

# Install packages that have C extensions but also provide pure-Python fallbacks
# PyYAML is a transitive dependency of strands-agents
pip install --target "$PACKAGE_DIR" --upgrade --no-deps pyyaml 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "   ERROR: pip install (pyyaml) failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit 1
}
$ErrorActionPreference = "Stop"

# Copy application code into the package
Write-Host "   Copying application code..." -ForegroundColor Gray
Copy-Item -Recurse "src" "$PACKAGE_DIR\src"
Copy-Item "handler.py" "$PACKAGE_DIR\handler.py"

# =============================================================================
# Step 3: Prune - Remove unnecessary files from package
# =============================================================================
Write-Host "[3/8] Pruning unnecessary files..." -ForegroundColor Yellow

# Remove boto3 and botocore (provided by Lambda runtime, saves ~80 MB)
@("boto3", "botocore") | ForEach-Object {
    $dir = Join-Path $PACKAGE_DIR $_
    if (Test-Path $dir) {
        # Retry removal in case files are temporarily locked by antivirus/indexer
        for ($attempt = 1; $attempt -le 3; $attempt++) {
            try {
                Remove-Item -Recurse -Force $dir -ErrorAction Stop
                Write-Host "   Removed $_" -ForegroundColor Gray
                break
            } catch {
                if ($attempt -lt 3) {
                    Write-Host "   File locked, retrying in 2 seconds... (attempt $attempt/3)" -ForegroundColor Gray
                    Start-Sleep -Seconds 2
                } else {
                    Write-Host "   WARNING: Could not fully remove $_ (file locked). Continuing anyway." -ForegroundColor Yellow
                }
            }
        }
    }
}

# Remove __pycache__ directories
Get-ChildItem -Path $PACKAGE_DIR -Directory -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
# Remove *.dist-info directories (keep opentelemetry ones - they need entry_points for plugin discovery)
Get-ChildItem -Path $PACKAGE_DIR -Directory -Recurse -Filter "*.dist-info" | Where-Object { $_.Name -notlike "opentelemetry*" } | Remove-Item -Recurse -Force
# Remove tests/ and test/ directories within dependency packages
Get-ChildItem -Path $PACKAGE_DIR -Directory -Recurse -Filter "tests" | Remove-Item -Recurse -Force
Get-ChildItem -Path $PACKAGE_DIR -Directory -Recurse -Filter "test" | Remove-Item -Recurse -Force
# Remove *.pyc and *.pyo files
Get-ChildItem -Path $PACKAGE_DIR -Recurse -Include "*.pyc", "*.pyo" -File | Remove-Item -Force
Write-Host "   Pruning complete" -ForegroundColor Gray

# =============================================================================
# Step 4: Zip - Create deployment package and report size
# =============================================================================
Write-Host "[4/8] Creating deployment package..." -ForegroundColor Yellow
$zipPath = "$BUILD_DIR\lambda-package.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }
Compress-Archive -Path "$PACKAGE_DIR\*" -DestinationPath $zipPath -Force

if (-not (Test-Path $zipPath)) {
    Write-Host "   ERROR: Failed to create zip package" -ForegroundColor Red
    exit 1
}

# Report compressed size
$compressedSizeMB = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Host "   Compressed size: ${compressedSizeMB} MB" -ForegroundColor Gray

# Estimate unzipped size (sum of all files in package directory)
$unzippedBytes = (Get-ChildItem -Path $PACKAGE_DIR -Recurse -File | Measure-Object -Property Length -Sum).Sum
$unzippedSizeMB = [math]::Round($unzippedBytes / 1MB, 1)
Write-Host "   Estimated unzipped size: ${unzippedSizeMB} MB" -ForegroundColor Gray

if ($unzippedSizeMB -gt 200) {
    Write-Host "   WARNING: Unzipped size exceeds 200 MB! Lambda limit is 250 MB." -ForegroundColor Red
}

# Compute content hash for S3 key (ensures unique key per unique package)
$zipHash = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash.ToLower()
$S3_KEY = "lambda-package-$($zipHash.Substring(0, 8)).zip"
Write-Host "   Package hash: $($zipHash.Substring(0, 8)) (SHA256)" -ForegroundColor Gray

# =============================================================================
# Step 5: Check Stack - Detect failed stack states and handle recovery
# =============================================================================
Write-Host "[5/8] Checking stack state..." -ForegroundColor Yellow

$stackStatus = $null
$stackInfo = aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION 2>&1
if ($LASTEXITCODE -eq 0) {
    $stackJson = $stackInfo | ConvertFrom-Json
    $stackStatus = $stackJson.Stacks[0].StackStatus
    Write-Host "   Stack status: $stackStatus" -ForegroundColor Gray
} else {
    Write-Host "   Stack does not exist yet - will create" -ForegroundColor Gray
}

# Handle stack states
if ($stackStatus -eq "ROLLBACK_COMPLETE") {
    Write-Host "`n   WARNING: Stack is in ROLLBACK_COMPLETE state." -ForegroundColor Red
    Write-Host "   The stack must be deleted before a new deployment can proceed." -ForegroundColor Red
    $confirm = Read-Host "   Delete stack '$STACK_NAME' and recreate? (y/N)"
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        Write-Host "   Deleting stack..." -ForegroundColor Yellow
        aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION
        Write-Host "   Waiting for stack deletion to complete..." -ForegroundColor Yellow
        aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $REGION
        if ($LASTEXITCODE -ne 0) {
            Write-Host "   ERROR: Stack deletion failed." -ForegroundColor Red
            exit 2
        }
        Write-Host "   Stack deleted successfully." -ForegroundColor Green
    } else {
        Write-Host "   Deployment aborted by user." -ForegroundColor Yellow
        exit 2
    }
} elseif ($stackStatus -eq "CREATE_IN_PROGRESS" -or $stackStatus -eq "UPDATE_IN_PROGRESS" -or $stackStatus -eq "DELETE_IN_PROGRESS") {
    Write-Host "`n   ERROR: Stack is currently in '$stackStatus' state." -ForegroundColor Red
    Write-Host "   Please wait for the current operation to complete and retry." -ForegroundColor Red
    exit 2
} elseif ($stackStatus -eq "UPDATE_ROLLBACK_COMPLETE" -or $stackStatus -eq "CREATE_COMPLETE" -or $stackStatus -eq "UPDATE_COMPLETE" -or $null -eq $stackStatus) {
    # Stack is in a stable state or doesn't exist - proceed with deployment
} else {
    Write-Host "   WARNING: Unexpected stack status '$stackStatus'. Attempting deployment anyway." -ForegroundColor Yellow
}

# =============================================================================
# Step 6: Upload - Push zip to S3 with content-hash key
# =============================================================================
Write-Host "[6/8] Uploading package to S3..." -ForegroundColor Yellow

# Create S3 bucket for deployment artifacts if it doesn't exist
$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ERROR: Failed to retrieve AWS account ID. Check AWS CLI configuration." -ForegroundColor Red
    exit 1
}

$S3_BUCKET = "orientation-mali-deploy-$ACCOUNT_ID"

$bucketExists = aws s3api head-bucket --bucket $S3_BUCKET 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "   Creating S3 bucket: $S3_BUCKET" -ForegroundColor Gray
    aws s3api create-bucket --bucket $S3_BUCKET --region $REGION
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ERROR: Failed to create S3 bucket." -ForegroundColor Red
        exit 1
    }
}

# Upload the package with content-hash key
Write-Host "   Uploading package to s3://$S3_BUCKET/$S3_KEY" -ForegroundColor Gray
aws s3 cp $zipPath "s3://$S3_BUCKET/$S3_KEY" --region $REGION
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ERROR: Failed to upload package to S3." -ForegroundColor Red
    exit 1
}

# =============================================================================
# Step 7: Deploy - Run CloudFormation deploy
# =============================================================================
Write-Host "[7/8] Deploying CloudFormation stack: $STACK_NAME..." -ForegroundColor Yellow

# NOTE: CloudFormation's default resource creation timeout is 60 minutes.
# This is sufficient for ACM certificate DNS validation, which typically
# completes in 5-30 minutes. The template uses DomainValidationOptions with
# HostedZoneId for automatic DNS record creation - no manual steps needed.
# The --no-fail-on-empty-changeset flag ensures idempotent re-deployments
# succeed even when no resource changes are detected.

$HOSTED_ZONE_ID = "Z08327853BYJS6IQVJSX5"
aws cloudformation deploy --template-file template-cf.yaml --stack-name $STACK_NAME --parameter-overrides S3Bucket=$S3_BUCKET S3Key=$S3_KEY DomainName=orientation-mali.com HostedZoneId=$HOSTED_ZONE_ID EnableCustomDomain=$EnableCustomDomain --capabilities CAPABILITY_NAMED_IAM --region $REGION --no-fail-on-empty-changeset

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n=== Deployment failed ===" -ForegroundColor Red
    Write-Host "   CloudFormation stack deployment returned a non-zero exit code." -ForegroundColor Red
    Write-Host "   If this was due to ACM certificate validation timeout, re-run the script" -ForegroundColor Red
    Write-Host "   after verifying the DNS validation record exists in Route 53." -ForegroundColor Red
    exit 3
}

Write-Host "`n=== Deployment successful! ===" -ForegroundColor Green

# Get the API URL from stack outputs
$apiUrl = aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='OrientationMaliApi'].OutputValue" --output text --region $REGION

Write-Host "API Gateway URL: $apiUrl" -ForegroundColor Cyan
if ($Mode -eq "full") {
    Write-Host "Custom Domain:   https://orientation-mali.com/" -ForegroundColor Cyan
}

# =============================================================================
# Step 8: Validate - Health check API Gateway and custom domain endpoints
# =============================================================================
Write-Host "`n[8/8] Verifying deployment (health checks)..." -ForegroundColor Yellow
$healthCheckFailed = $false

# 8a. Health check against API Gateway endpoint
if ($apiUrl -and $apiUrl -ne "None") {
    Write-Host "   Checking API Gateway endpoint: $apiUrl" -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri $apiUrl -Method GET -TimeoutSec 30 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "   API Gateway health check: PASSED (200 OK)" -ForegroundColor Green
        } else {
            $truncatedBody = $response.Content.Substring(0, [Math]::Min(200, $response.Content.Length))
            Write-Host "   API Gateway health check: FAILED (Status: $($response.StatusCode))" -ForegroundColor Red
            Write-Host "   Response body: $truncatedBody" -ForegroundColor Red
            $healthCheckFailed = $true
        }
    } catch {
        $statusCode = $null
        $body = ""
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
            try {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $body = $reader.ReadToEnd()
                $reader.Close()
            } catch { $body = $_.Exception.Message }
        } else { $body = $_.Exception.Message }
        $truncatedBody = if ($body.Length -gt 200) { $body.Substring(0, 200) } else { $body }
        if ($statusCode) {
            Write-Host "   API Gateway health check: FAILED (Status: $statusCode)" -ForegroundColor Red
        } else {
            Write-Host "   API Gateway health check: FAILED (Connection error)" -ForegroundColor Red
        }
        Write-Host "   Details: $truncatedBody" -ForegroundColor Red
        $healthCheckFailed = $true
    }
} else {
    Write-Host "   WARNING: Could not retrieve API Gateway URL from stack outputs" -ForegroundColor Yellow
    $healthCheckFailed = $true
}

# 8b. Health check against custom domain (full mode only)
if ($Mode -eq "full") {
    $customDomainUrl = "https://orientation-mali.com/"
    Write-Host "   Checking custom domain: $customDomainUrl" -ForegroundColor Gray
    Write-Host "   Waiting for DNS propagation (up to 60 seconds)..." -ForegroundColor Gray

    $dnsReady = $false
    $maxWaitSeconds = 60
    $pollIntervalSeconds = 10
    $elapsed = 0

    while ($elapsed -lt $maxWaitSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $customDomainUrl -Method GET -TimeoutSec 30 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Host "   Custom domain health check: PASSED (200 OK)" -ForegroundColor Green
                $dnsReady = $true
                break
            } else {
                Write-Host "   Custom domain health check: FAILED (Status: $($response.StatusCode))" -ForegroundColor Red
                $healthCheckFailed = $true
                $dnsReady = $true
                break
            }
        } catch {
            $statusCode = $null
            if ($_.Exception.Response) { $statusCode = [int]$_.Exception.Response.StatusCode }
            if ($statusCode) {
                Write-Host "   Custom domain health check: FAILED (Status: $statusCode)" -ForegroundColor Red
                $healthCheckFailed = $true
                $dnsReady = $true
                break
            }
            # DNS not yet propagated or connection failed - retry
            $elapsed += $pollIntervalSeconds
            if ($elapsed -lt $maxWaitSeconds) {
                Write-Host "   DNS not ready yet, retrying in $pollIntervalSeconds seconds... ($elapsed/$maxWaitSeconds)" -ForegroundColor Gray
                Start-Sleep -Seconds $pollIntervalSeconds
            }
        }
    }

    if (-not $dnsReady) {
        Write-Host "   Custom domain health check: FAILED (DNS did not propagate within $maxWaitSeconds seconds)" -ForegroundColor Red
        $healthCheckFailed = $true
    }
}

# Health check summary and exit
if ($healthCheckFailed) {
    Write-Host "`n   WARNING: One or more health checks failed. Deployment completed but verification failed." -ForegroundColor Yellow
    exit 4
} else {
    Write-Host "`n   All health checks passed." -ForegroundColor Green
    exit 0
}
