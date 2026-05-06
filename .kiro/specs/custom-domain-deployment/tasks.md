# Implementation Plan: Custom Domain Deployment

## Overview

Enhance the existing `deploy.ps1` and `template-cf.yaml` to support reliable custom domain deployment with package optimization, two-phase deployment, stack recovery, and post-deploy health checks. All tasks modify existing files — no new source files are created.

## Tasks

- [x] 1. Add EnableCustomDomain condition to CloudFormation template
  - [x] 1.1 Add EnableCustomDomain parameter and condition to template-cf.yaml
    - Add `EnableCustomDomain` parameter (String, default `"true"`, allowed values `"true"` / `"false"`)
    - Add `DeployCustomDomain` condition: `!Equals [!Ref EnableCustomDomain, "true"]`
    - _Requirements: 7.3_

  - [x] 1.2 Apply condition to custom domain resources
    - Add `Condition: DeployCustomDomain` to `Certificate`, `ApiDomainName`, `ApiMapping`, and `DnsRecord` resources
    - Add condition to `CustomDomainUrl` output using `!If [DeployCustomDomain, ...]`
    - Ensure `DependsOn` relationships remain correct (Certificate before ApiDomainName, HttpApiStage before ApiMapping)
    - _Requirements: 4.2, 4.3, 7.3_

  - [x] 1.3 Validate template syntax
    - Run `aws cloudformation validate-template --template-body file://template-cf.yaml`
    - Verify no syntax errors after condition additions
    - _Requirements: 4.1_

- [x] 2. Enhance deploy.ps1 with -Mode parameter and deployment phases
  - [x] 2.1 Add -Mode parameter and script configuration
    - Add `param([ValidateSet("full","base")][string]$Mode = "full")` at the top of deploy.ps1
    - Update script header documentation to describe the new parameter
    - Set `$EnableCustomDomain` variable based on `$Mode` ("true" for full, "false" for base)
    - _Requirements: 7.1, 7.2, 7.5_

  - [x] 2.2 Pass EnableCustomDomain parameter to CloudFormation deploy command
    - Add `EnableCustomDomain=$EnableCustomDomain` to the `--parameter-overrides` in the `aws cloudformation deploy` call
    - _Requirements: 7.3, 7.4_

- [x] 3. Implement Lambda package size optimization
  - [x] 3.1 Exclude boto3 and botocore from pip install
    - After pip install steps, remove `boto3` and `botocore` directories from `$PACKAGE_DIR` (these are provided by the Lambda runtime)
    - _Requirements: 2.1, 2.3_

  - [x] 3.2 Prune unnecessary files from package
    - Remove all `__pycache__` directories recursively from `$PACKAGE_DIR`
    - Remove all `*.dist-info` directories from `$PACKAGE_DIR`
    - Remove all `tests/` and `test/` directories within dependency packages
    - Remove `*.pyc` and `*.pyo` files
    - _Requirements: 2.2_

  - [x] 3.3 Report package size (compressed and estimated unzipped)
    - After creating the zip, report compressed size in MB
    - Estimate unzipped size (sum of file sizes in `$PACKAGE_DIR`) and report in MB
    - Warn if estimated unzipped size exceeds 200 MB
    - _Requirements: 2.4, 2.5_

- [x] 4. Implement content-hash S3 key for deployment packages
  - [x] 4.1 Compute SHA256 hash of the zip file and construct S3 key
    - After creating the zip, compute SHA256 hash using `Get-FileHash`
    - Construct S3 key as `lambda-package-{first-8-chars-of-hash}.zip`
    - Use this key for the S3 upload and CloudFormation parameter
    - _Requirements: 3.3, 6.2_

- [x] 5. Implement stack state detection and recovery
  - [x] 5.1 Query stack status before deployment
    - Before the CloudFormation deploy command, query the stack status using `aws cloudformation describe-stacks`
    - Handle the case where the stack does not exist (command returns error)
    - _Requirements: 6.1, 6.3_

  - [x] 5.2 Handle ROLLBACK_COMPLETE state with deletion prompt
    - If stack status is `ROLLBACK_COMPLETE`, display a warning and prompt the user to confirm deletion
    - If confirmed, run `aws cloudformation delete-stack` and `aws cloudformation wait stack-delete-complete`
    - If declined, exit with code 2
    - _Requirements: 6.1_

  - [x] 5.3 Handle other stack states
    - If `CREATE_IN_PROGRESS`, `UPDATE_IN_PROGRESS`, or `DELETE_IN_PROGRESS`: exit with message to retry later
    - If `UPDATE_ROLLBACK_COMPLETE`, `CREATE_COMPLETE`, or `UPDATE_COMPLETE`: proceed with update
    - _Requirements: 6.3_

- [x] 6. Checkpoint - Validate template and script structure
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement post-deployment health checks
  - [x] 7.1 Health check against API Gateway endpoint
    - After successful CloudFormation deployment, retrieve the API Gateway URL from stack outputs
    - Perform an HTTP GET request using `Invoke-WebRequest` with a 30-second timeout
    - Verify 200 status code; report failure with status code and truncated response body
    - _Requirements: 8.1, 8.3_

  - [x] 7.2 Health check against custom domain (full mode only)
    - Only when `$Mode -eq "full"`, wait up to 60 seconds for DNS propagation (poll every 10 seconds)
    - Perform HTTP GET to `https://orientation-mali.com/`
    - Report result (success or failure with status code)
    - Health check failure produces a warning but does not fail the script (exit code 0 still)
    - _Requirements: 8.2, 8.4_

- [x] 8. Wire everything together and finalize script flow
  - [x] 8.1 Restructure deploy.ps1 step numbering and flow
    - Update step numbering to reflect new phases: Clean → Package → Prune → Zip → Check Stack → Upload → Deploy → Validate
    - Ensure all steps execute in correct order with proper error handling (`$LASTEXITCODE` checks)
    - Set appropriate exit codes per the design (0=success, 1=packaging failure, 2=stack unrecoverable, 3=CF failure, 4=health check warning)
    - _Requirements: 1.4, 1.5, 4.4, 4.5, 4.6_

  - [x] 8.2 Ensure deployment timeout is sufficient for ACM validation
    - The default CloudFormation timeout (60 minutes) is sufficient; document this in script comments
    - Ensure `--no-fail-on-empty-changeset` flag is present
    - _Requirements: 1.4, 6.4_

- [x] 9. Final checkpoint - Validate complete deployment script
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- No property-based tests are included — this feature is entirely IaC and deployment scripting with no pure functions to test
- All implementation is in PowerShell (deploy.ps1) and CloudFormation YAML (template-cf.yaml)
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
