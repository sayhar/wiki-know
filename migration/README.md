# Imgur to S3 Migration

This folder contains the migration scripts and documentation for moving screenshots from Imgur to AWS S3.

## Files

- `imgur_migration.py` - Main migration script
- `test_migration.py` - Test script for migration components
- `aws_config.md` - AWS setup instructions
- `MIGRATION_README.md` - Detailed migration documentation

## Usage

From the project root directory:

```bash
# Run migration from migration folder
cd migration
uv run python imgur_migration.py

# Test migration components
uv run python test_migration.py
```

## Important Notes

- The migration script expects to be run from the `migration/` folder
- CSV files are located at `../static/report/` relative to this folder
- Progress files are saved in this folder
- AWS credentials must be configured before running
