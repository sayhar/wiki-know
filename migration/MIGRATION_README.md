# Imgur to S3 Migration Guide

This guide explains how to migrate imgur screenshots to S3 using the `imgur_migration.py` script.

## Overview

The migration script will:

1. Scan all `screenshots.csv` files in the `static/report` directory
2. Extract imgur URLs from the CSV files
3. Download images from imgur
4. Upload to S3 in two locations:
   - `s3://wikitoy/screenshotsImgur/<imgur_id>.<ext>` - Direct copy
   - `s3://wikitoy/screenshotsClean/<testname>/<optionName>` - Organized structure
5. Generate a lookup table for URL mapping
6. Track progress and allow resuming

## Prerequisites

1. **AWS Configuration**: Follow `aws_config.md` to set up AWS credentials
2. **Dependencies**: Install required Python packages:
   ```bash
   uv sync
   ```

## Usage

### 1. Dry Run (Recommended First Step)

Test the migration without making changes:

```bash
python imgur_migration.py --dry-run
```

This will:

- Scan all CSV files
- Show what would be uploaded
- Not download or upload anything
- Generate a preview of the migration

### 2. Full Migration

Run the actual migration:

```bash
python imgur_migration.py
```

### 3. Resume Migration

If the migration is interrupted, resume from where it left off:

```bash
python imgur_migration.py --resume
```

### 4. Clean Up

Remove temporary files after successful migration:

```bash
python imgur_migration.py --cleanup
```

## Command Line Options

```bash
python imgur_migration.py [OPTIONS]

Options:
  --dry-run      Run in dry-run mode (no actual changes)
  --resume       Resume from previous run
  --cleanup      Clean up temporary files
  --report-dir   Directory containing report files (default: static/report)
  --bucket       S3 bucket name (default: wikitoy)
  --help         Show help message
```

## Migration Structure

### S3 Organization

```
s3://wikitoy/
├── screenshotsImgur/           # Direct imgur copies
│   ├── aMHgu8d.png
│   ├── brWoqHJ.png
│   └── ...
└── screenshotsClean/           # Organized by test
    ├── 1366633701Bolding/
    │   ├── Key.phrases.are.bolded.png
    │   └── All.of.the.text.is.bolded.png
    ├── 1366635965Banner.design/
    │   ├── if.everyone.reading.this.is.in.blue.png
    │   └── all.text.in.black.png
    └── ...
```

### URL Mapping

The script creates a lookup table mapping:

- **Original imgur URL** → **S3 screenshotsClean URL** (primary)
- **Original imgur URL** → **S3 screenshotsImgur URL** (fallback)

## Progress Tracking

The script automatically tracks progress in:

- `migration_progress.json` - Current progress
- `migration_report.json` - Final report
- `imgur_migration.log` - Detailed logs

## Error Handling

- **Network failures**: Automatic retries with exponential backoff
- **Invalid URLs**: Logged and skipped
- **S3 upload failures**: Logged and marked as failed
- **Interruptions**: Progress saved, can resume later

## Performance Considerations

- **Rate limiting**: 0.1 second delay between downloads to be respectful to imgur
- **Batch processing**: Processes all URLs in sequence
- **Resume capability**: Can stop and resume at any time
- **Duplicate handling**: Automatically skips already processed URLs

## Monitoring

Watch the migration progress:

```bash
# Follow logs in real-time
tail -f imgur_migration.log

# Check progress
cat migration_progress.json | jq '.processed_urls | length'
```

## Post-Migration

After successful migration:

1. **Update your application code** to use the new S3 URLs
2. **Test the new URLs** to ensure they work correctly
3. **Clean up temporary files** using `--cleanup` flag
4. **Verify S3 uploads** by checking the bucket contents

## Troubleshooting

### Common Issues

1. **AWS credentials not found**

   - Follow `aws_config.md` to configure credentials
   - Test with `aws s3 ls s3://wikitoy/`

2. **Permission denied on S3 bucket**

   - Ensure your AWS user has the required S3 permissions
   - Check bucket policy and IAM roles

3. **Network timeouts**

   - The script includes retry logic
   - Check your internet connection
   - Consider running during off-peak hours

4. **CSV parsing errors**
   - Check CSV file encoding (should be UTF-8)
   - Verify CSV structure matches expected format

### Getting Help

- Check the log file: `imgur_migration.log`
- Review progress files: `migration_progress.json`
- Ensure all dependencies are installed
- Verify AWS configuration

## Security Notes

- **AWS credentials**: Never commit credentials to version control
- **S3 permissions**: Use least-privilege access
- **Image content**: Downloaded images are uploaded as-is to S3
- **Logs**: May contain URLs and file paths - review before sharing

## Future Enhancements

Potential improvements for future versions:

- Parallel processing for faster migration
- CloudFront distribution for faster access
- Image optimization and compression
- Automated testing of migrated URLs
- Integration with existing application code
