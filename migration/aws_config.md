# AWS Configuration for Imgur Migration

This document explains how to configure AWS credentials for the imgur migration script.

## Prerequisites

1. AWS account with access to the `wikitoy` S3 bucket
2. AWS CLI installed and configured, or environment variables set

## Option 1: AWS CLI Configuration (Recommended)

1. Install AWS CLI:

   ```bash
   # macOS
   brew install awscli

   # Linux
   pip install awscli
   ```

2. Configure AWS credentials:

   ```bash
   aws configure
   ```

   Enter your:

   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (e.g., us-east-1)
   - Default output format (json)

## Option 2: Environment Variables

Set these environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_DEFAULT_REGION=us-east-1
```

## Option 3: IAM Role (if running on EC2)

If running on an EC2 instance, attach an IAM role with S3 permissions.

## Required S3 Permissions

Your AWS user/role needs these permissions on the `wikitoy` bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:HeadBucket"
      ],
      "Resource": ["arn:aws:s3:::wikitoy", "arn:aws:s3:::wikitoy/*"]
    }
  ]
}
```

## Testing Configuration

Test your AWS configuration:

```bash
aws s3 ls s3://wikitoy/
```

If successful, you should see the bucket contents.

## Troubleshooting

- **NoCredentialsError**: AWS credentials not found
- **AccessDenied**: Insufficient permissions on the bucket
- **NoSuchBucket**: Bucket doesn't exist or wrong region
