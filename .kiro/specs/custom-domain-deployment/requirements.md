# Requirements Document

## Introduction

This specification covers the reliable deployment of the Orientation Mali application to the custom domain "orientation-mali.com" using AWS CloudFormation. The application is already deployed as a Lambda function behind API Gateway HTTP API, and the domain is registered in Route 53. The primary challenge is making the deployment process robust — specifically handling ACM certificate DNS validation (which can take 30+ minutes), managing Lambda package size constraints (250 MB unzipped limit), and ensuring the CloudFormation stack deploys successfully in a single operation without timeouts or failures.

## Glossary

- **Deployment_Script**: The PowerShell script (deploy.ps1) that packages the Lambda function, uploads it to S3, and deploys the CloudFormation stack
- **CloudFormation_Template**: The template-cf.yaml file defining all AWS resources for the application infrastructure
- **ACM_Certificate**: An AWS Certificate Manager SSL/TLS certificate for the custom domain, validated via DNS
- **DNS_Validation_Record**: A CNAME record created in Route 53 that proves domain ownership to ACM for certificate issuance
- **Custom_Domain**: The API Gateway V2 custom domain name resource (orientation-mali.com) that maps to the HTTP API
- **API_Mapping**: The API Gateway V2 resource that connects the Custom_Domain to the HTTP API stage
- **Lambda_Package**: The zip archive containing application code and all Python dependencies, uploaded to S3 for Lambda deployment
- **Route53_Alias_Record**: An A record in Route 53 that points orientation-mali.com to the API Gateway regional domain name
- **Deployment_Bucket**: The S3 bucket (orientation-mali-deploy-{ACCOUNT_ID}) used to store the Lambda_Package
- **Stack**: The CloudFormation stack named "orientation-mali" that manages all application resources

## Requirements

### Requirement 1: ACM Certificate Provisioning with Reliable DNS Validation

**User Story:** As a developer, I want the ACM certificate to be provisioned and validated reliably within CloudFormation, so that the deployment does not time out or fail waiting for certificate validation.

#### Acceptance Criteria

1. THE CloudFormation_Template SHALL define an ACM_Certificate resource with DNS validation method for the domain "orientation-mali.com"
2. THE CloudFormation_Template SHALL configure the ACM_Certificate DomainValidationOptions to reference the Route 53 Hosted Zone ID (Z08327853BYJS6IQVJSX5) for automatic DNS_Validation_Record creation
3. WHEN CloudFormation creates the ACM_Certificate, THE CloudFormation_Template SHALL ensure the DNS_Validation_Record is created in Route 53 before the certificate validation check begins
4. THE Deployment_Script SHALL set a CloudFormation deployment timeout sufficient for ACM certificate validation (minimum 45 minutes)
5. IF the CloudFormation stack deployment fails due to certificate validation timeout, THEN THE Deployment_Script SHALL provide a clear error message indicating the certificate validation status

### Requirement 2: Lambda Package Size Optimization

**User Story:** As a developer, I want the Lambda deployment package to stay within AWS size limits, so that deployments do not fail due to package size constraints.

#### Acceptance Criteria

1. THE Deployment_Script SHALL produce a Lambda_Package that does not exceed 250 MB when unzipped
2. THE Deployment_Script SHALL exclude unnecessary files from the Lambda_Package including test files, documentation, __pycache__ directories, and .dist-info metadata
3. THE Deployment_Script SHALL install only production dependencies required for Lambda execution
4. THE Deployment_Script SHALL report the final Lambda_Package size (both compressed and estimated unzipped) after packaging
5. IF the Lambda_Package exceeds 50 MB compressed (S3 upload limit for direct deployment), THEN THE Deployment_Script SHALL upload the package to the Deployment_Bucket and reference it via S3

### Requirement 3: S3 Deployment Bucket Management

**User Story:** As a developer, I want the deployment bucket to be created and managed automatically, so that I do not need manual setup steps before deploying.

#### Acceptance Criteria

1. WHEN the Deployment_Script runs, THE Deployment_Script SHALL determine the AWS account ID and construct the Deployment_Bucket name as "orientation-mali-deploy-{ACCOUNT_ID}"
2. IF the Deployment_Bucket does not exist, THEN THE Deployment_Script SHALL create the Deployment_Bucket in the us-east-1 region
3. THE Deployment_Script SHALL upload the Lambda_Package to the Deployment_Bucket with a versioned key that includes a timestamp or hash to prevent caching issues
4. THE CloudFormation_Template SHALL reference the Deployment_Bucket and S3 key via parameters for the Lambda function Code property

### Requirement 4: CloudFormation Stack Deployment

**User Story:** As a developer, I want the CloudFormation stack to deploy all resources (Lambda, API Gateway, DynamoDB, custom domain, DNS) in a single operation, so that the infrastructure is consistent and reproducible.

#### Acceptance Criteria

1. THE CloudFormation_Template SHALL define all required resources: Lambda function, IAM role, API Gateway HTTP API, API Gateway integration, routes, stage, DynamoDB table, ACM_Certificate, Custom_Domain, API_Mapping, and Route53_Alias_Record
2. THE CloudFormation_Template SHALL define explicit DependsOn relationships ensuring the ACM_Certificate is validated before the Custom_Domain resource is created
3. THE CloudFormation_Template SHALL define explicit DependsOn relationships ensuring the API Gateway stage exists before the API_Mapping is created
4. WHEN the Stack deployment succeeds, THE Deployment_Script SHALL output both the API Gateway endpoint URL and the custom domain URL (https://orientation-mali.com/)
5. THE Deployment_Script SHALL use the --no-fail-on-empty-changeset flag to handle idempotent re-deployments gracefully
6. THE CloudFormation_Template SHALL use the CAPABILITY_IAM capability for IAM role creation

### Requirement 5: Custom Domain DNS Configuration

**User Story:** As a developer, I want the DNS to be configured automatically so that orientation-mali.com resolves to the API Gateway endpoint after deployment.

#### Acceptance Criteria

1. THE CloudFormation_Template SHALL create a Route53_Alias_Record of type A in the hosted zone Z08327853BYJS6IQVJSX5
2. THE Route53_Alias_Record SHALL point to the API Gateway Custom_Domain regional domain name
3. THE Route53_Alias_Record SHALL use the API Gateway Custom_Domain regional hosted zone ID as the alias target hosted zone
4. WHEN the Stack deployment completes successfully, THE Custom_Domain SHALL serve HTTPS traffic at https://orientation-mali.com/

### Requirement 6: Deployment Idempotency and Recovery

**User Story:** As a developer, I want to be able to re-run the deployment script safely after a failure, so that I can recover from partial deployments without manual cleanup.

#### Acceptance Criteria

1. WHEN the Deployment_Script is run against an existing Stack in a failed state (ROLLBACK_COMPLETE or UPDATE_ROLLBACK_COMPLETE), THE Deployment_Script SHALL detect the failed state and offer to delete and recreate the stack
2. THE Deployment_Script SHALL use unique S3 keys for each deployment to avoid serving stale Lambda code from cached packages
3. WHEN the Stack already exists and is in a stable state (CREATE_COMPLETE or UPDATE_COMPLETE), THE Deployment_Script SHALL perform an update deployment
4. IF no changes are detected in the Stack, THEN THE Deployment_Script SHALL report success without error (no-fail-on-empty-changeset behavior)

### Requirement 7: Two-Phase Deployment Strategy

**User Story:** As a developer, I want the option to deploy base infrastructure separately from the custom domain resources, so that I can avoid ACM certificate timeout issues blocking the entire deployment.

#### Acceptance Criteria

1. THE Deployment_Script SHALL support a parameter or flag to deploy only base infrastructure (Lambda, API Gateway, DynamoDB) without custom domain resources
2. THE Deployment_Script SHALL support a parameter or flag to deploy the full stack including custom domain resources (ACM_Certificate, Custom_Domain, API_Mapping, Route53_Alias_Record)
3. WHEN deploying in base-only mode, THE CloudFormation_Template SHALL use a CloudFormation condition to skip custom domain resources
4. WHEN deploying in full mode with an existing validated ACM_Certificate, THE CloudFormation_Template SHALL reuse the existing certificate without re-validation
5. THE Deployment_Script SHALL default to full deployment mode when no flag is specified

### Requirement 8: Deployment Validation and Health Check

**User Story:** As a developer, I want the deployment script to verify the application is working after deployment, so that I have confidence the deployment succeeded end-to-end.

#### Acceptance Criteria

1. WHEN the Stack deployment completes successfully, THE Deployment_Script SHALL perform an HTTP GET request to the API Gateway endpoint URL and verify a 200 status code response
2. WHEN deploying with custom domain enabled and the Stack deployment completes, THE Deployment_Script SHALL perform an HTTP GET request to https://orientation-mali.com/ and report the result
3. IF the health check to the API Gateway endpoint fails, THEN THE Deployment_Script SHALL report the failure with the HTTP status code and response body
4. THE Deployment_Script SHALL wait up to 60 seconds for DNS propagation before performing the custom domain health check
