#!/usr/bin/env python3
"""
Imgur to S3 Migration Script

This script migrates imgur screenshots to S3 with the following structure:
1. s3://wikitoy/screenshotsImgur/<imgur_id>.<ext> - Direct copy of imgur image
2. s3://wikitoy/screenshotsClean/<testname>/<optionName> - Clean organized structure

Features:
- Dry run mode to preview changes
- Resume capability with progress tracking
- Graceful error handling and retries
- Progress reporting and logging
- Lookup table generation for URL mapping
"""

import os
import csv
import json
import time
import hashlib
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse
import requests
import boto3
import pandas as pd
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("imgur_migration.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class ImgurMigration:
    def __init__(
        self,
        bucket_name: str = "wikitoy",
        dry_run: bool = False,
        limit: Optional[int] = None,
    ):
        self.bucket_name = bucket_name
        self.dry_run = dry_run
        self.limit = limit
        self.s3_client = None
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; WikiGuess-Imgur-Migration/1.0)"}
        )

        # Progress tracking
        self.progress_file = "migration_progress.json"
        self.lookup_file = "imgur_to_s3_lookup.json"
        self.processed_urls: set[str] = set()
        self.failed_urls: set[str] = set()

        # Load existing progress
        self.load_progress()

        # Initialize S3 client if not dry run
        if not dry_run:
            try:
                self.s3_client = boto3.client("s3")
                # Test S3 connection
                self.s3_client.head_bucket(Bucket=bucket_name)
                logger.info(f"Successfully connected to S3 bucket: {bucket_name}")
            except NoCredentialsError:
                logger.error(
                    "AWS credentials not found. Please configure your AWS credentials."
                )
                raise
            except ClientError as e:
                logger.error(f"Failed to access S3 bucket {bucket_name}: {e}")
                raise
        else:
            logger.info("DRY RUN MODE - No actual changes will be made")

    def load_progress(self):
        """Load existing progress from file"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, "r") as f:
                    data = json.load(f)
                    self.processed_urls = set(data.get("processed_urls", []))
                    self.failed_urls = set(data.get("failed_urls", []))
                logger.info(
                    f"Loaded progress: {len(self.processed_urls)} processed, {len(self.failed_urls)} failed"
                )
            except Exception as e:
                logger.warning(f"Failed to load progress file: {e}")

    def save_progress(self):
        """Save current progress to file"""
        data = {
            "processed_urls": list(self.processed_urls),
            "failed_urls": list(self.failed_urls),
            "timestamp": time.time(),
        }
        with open(self.progress_file, "w") as f:
            json.dump(data, f, indent=2)

    def extract_imgur_id(self, url: str) -> Optional[str]:
        """Extract imgur ID from URL"""
        if not url or url == "NA":
            return None

        # Handle various imgur URL formats
        if "i.imgur.com" in url:
            # Extract filename without extension
            filename = url.split("/")[-1]
            return filename.split(".")[0]
        elif "imgur.com" in url:
            # Handle imgur.com URLs
            path = urlparse(url).path
            if path.startswith("/"):
                path = path[1:]
            return path.split("/")[-1].split(".")[0]

        return None

    def download_image(self, url: str, max_retries: int = 3) -> Optional[bytes]:
        """Download image from imgur with retries"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                # Check if it's actually an image
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    logger.warning(
                        f"URL {url} returned non-image content: {content_type}"
                    )
                    return None

                return response.content
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Download attempt {attempt + 1} failed for {url}: {e}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Failed to download {url} after {max_retries} attempts: {e}"
                    )
                    return None

        return None

    def upload_to_s3(
        self, key: str, data: bytes, content_type: Optional[str] = None
    ) -> bool:
        """Upload data to S3"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would upload to s3://{self.bucket_name}/{key}")
            return True

        try:
            if not self.s3_client:
                logger.error("S3 client not initialized")
                return False

            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            # Make files publicly readable
            extra_args["ACL"] = "public-read"

            self.s3_client.put_object(
                Bucket=self.bucket_name, Key=key, Body=data, **extra_args
            )
            logger.info(f"Successfully uploaded to s3://{self.bucket_name}/{key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload to s3://{self.bucket_name}/{key}: {e}")
            return False

    def get_content_type(self, url: str, data: bytes) -> str:
        """Determine content type from URL and data"""
        # Try to get from URL extension first
        parsed = urlparse(url)
        path = parsed.path.lower()

        if path.endswith(".png"):
            return "image/png"
        elif path.endswith(".jpg") or path.endswith(".jpeg"):
            return "image/jpeg"
        elif path.endswith(".gif"):
            return "image/gif"
        elif path.endswith(".webp"):
            return "image/webp"

        # Fallback: try to determine from data
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        elif data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
            return "image/gif"

        return "application/octet-stream"

    def process_csv_file(self, csv_path: str) -> List[Dict]:
        """Process a single CSV file and extract imgur URLs"""
        imgur_entries = []

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Check all screenshot columns (handle both dot and underscore naming)
                    screenshot_cols = [
                        "screenshot",
                        "extra.screenshot.1",
                        "extra.screenshot.2",
                        "extra_screenshot_1",
                        "extra_screenshot_2",
                    ]

                    for col in screenshot_cols:
                        if col in row and row[col] and row[col] != "NA":
                            imgur_id = self.extract_imgur_id(row[col])
                            if imgur_id:
                                imgur_entries.append(
                                    {
                                        "url": row[col],
                                        "imgur_id": imgur_id,
                                        "testname": row.get("testname", ""),
                                        "value": row.get("value", ""),
                                        "csv_file": csv_path,
                                    }
                                )

        except Exception as e:
            logger.error(f"Error processing CSV file {csv_path}: {e}")

        return imgur_entries

    def find_csv_files(self, report_dir: str = "../static/report") -> List[str]:
        """Find all CSV files in the report directory"""
        csv_files: List[str] = []
        report_path = Path(report_dir)

        if not report_path.exists():
            logger.error(f"Report directory {report_dir} does not exist")
            return csv_files

        # Find all screenshots.csv files
        for csv_file in report_path.rglob("screenshots.csv"):
            csv_files.append(str(csv_file))

        logger.info(f"Found {len(csv_files)} screenshots.csv files")
        return csv_files

    def migrate_imgur_url(self, entry: Dict) -> bool:
        """Migrate a single imgur URL to S3"""
        url = entry["url"]
        imgur_id = entry["imgur_id"]
        testname = entry["testname"]
        value = entry["value"]

        # Skip if already processed
        if url in self.processed_urls:
            logger.debug(f"Skipping already processed URL: {url}")
            return True

        # Skip if previously failed
        if url in self.failed_urls:
            logger.debug(f"Skipping previously failed URL: {url}")
            return False

        # Check if already exists in S3 (either location)
        if self.dry_run:
            logger.debug(f"[DRY RUN] Would check S3 existence for: {url}")
        elif self.s3_client:
            # Check screenshotsImgur first
            imgur_key = f"screenshotsImgur/{imgur_id}.png"  # Assume PNG for now
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=imgur_key)
                logger.info(
                    f"Already exists in S3: s3://{self.bucket_name}/{imgur_key}"
                )
                self.processed_urls.add(url)
                self.save_progress()
                return True
            except:
                pass  # File doesn't exist, continue with migration

        logger.info(f"Processing: {url} -> {imgur_id}")

        # Download image
        image_data = self.download_image(url)
        if not image_data:
            self.failed_urls.add(url)
            self.save_progress()
            return False

        # Determine content type and file extension
        content_type = self.get_content_type(url, image_data)
        file_ext = content_type.split("/")[-1]
        if file_ext == "jpeg":
            file_ext = "jpg"

        # Upload to screenshotsImgur directory
        imgur_key = f"screenshotsImgur/{imgur_id}.{file_ext}"
        if not self.upload_to_s3(imgur_key, image_data, content_type):
            self.failed_urls.add(url)
            self.save_progress()
            return False

        # Upload to screenshotsClean directory
        if testname and value:
            # Clean the value for use as filename
            clean_value = value.replace("/", "_").replace("\\", "_").replace(" ", "_")
            clean_key = f"screenshotsClean/{testname}/{clean_value}.{file_ext}"

            if not self.upload_to_s3(clean_key, image_data, content_type):
                logger.warning(f"Failed to upload clean version for {url}")
                # Don't mark as failed for main upload, just warn
        else:
            logger.warning(
                f"Skipping screenshotsClean upload for {url} - missing metadata: testname='{testname}', value='{value}'"
            )

        # Mark as processed
        self.processed_urls.add(url)
        self.save_progress()

        return True

    def generate_lookup_table(self) -> Dict[str, str]:
        """Generate lookup table for imgur URLs to S3 URLs"""
        lookup: Dict[str, str] = {}

        for entry in self.processed_urls:
            # This would need to be enhanced to store the actual S3 keys
            # For now, we'll generate them programmatically
            pass

        return lookup

    def run_migration(self, report_dir: str = "../static/report"):
        """Run the complete migration process"""
        logger.info("Starting imgur migration process...")

        # Find all CSV files
        csv_files = self.find_csv_files(report_dir)
        if not csv_files:
            logger.error("No CSV files found")
            return

        # Process each CSV file
        all_entries = []
        for csv_file in csv_files:
            logger.info(f"Processing {csv_file}")
            entries = self.process_csv_file(csv_file)
            all_entries.extend(entries)

        logger.info(f"Found {len(all_entries)} imgur URLs to process")

        # Remove duplicates based on URL
        unique_entries = {entry["url"]: entry for entry in all_entries}.values()
        logger.info(f"After deduplication: {len(unique_entries)} unique URLs")

        # Process each unique URL
        successful = 0
        failed = 0

        for i, entry in enumerate(unique_entries, 1):
            logger.info(f"Processing {i}/{len(unique_entries)}: {entry['url']}")

            if self.migrate_imgur_url(entry):
                successful += 1
            else:
                failed += 1

            # Add small delay to be respectful to imgur
            time.sleep(0.1)

            # Check if we've hit the limit
            if hasattr(self, "limit") and self.limit and i >= self.limit:
                logger.info(f"Reached limit of {self.limit} URLs. Stopping migration.")
                break

        logger.info(f"Migration completed: {successful} successful, {failed} failed")

        # Generate final report
        self.generate_final_report()

    def generate_final_report(self):
        """Generate a final migration report"""
        report = {
            "timestamp": time.time(),
            "total_processed": len(self.processed_urls),
            "total_failed": len(self.failed_urls),
            "processed_urls": list(self.processed_urls),
            "failed_urls": list(self.failed_urls),
        }

        report_file = "migration_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Migration report saved to {report_file}")

    def resume_migration(self, report_dir: str = "../static/report"):
        """Resume migration from where it left off"""
        logger.info("Resuming migration...")
        self.run_migration(report_dir)

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        temp_files = [self.progress_file, self.lookup_file]
        for file in temp_files:
            if os.path.exists(file):
                os.remove(file)
                logger.info(f"Removed temporary file: {file}")


def main():
    parser = argparse.ArgumentParser(description="Migrate imgur screenshots to S3")
    parser.add_argument(
        "--dry-run", action="store_true", help="Run in dry-run mode (no actual changes)"
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume from previous run"
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Clean up temporary files"
    )
    parser.add_argument(
        "--limit", type=int, help="Limit number of URLs to process (for testing)"
    )
    parser.add_argument(
        "--report-dir",
        default="../static/report",
        help="Directory containing report files",
    )
    parser.add_argument("--bucket", default="wikitoy", help="S3 bucket name")

    args = parser.parse_args()

    if args.cleanup:
        migration = ImgurMigration(bucket_name=args.bucket, dry_run=True)
        migration.cleanup_temp_files()
        return

    try:
        migration = ImgurMigration(
            bucket_name=args.bucket, dry_run=args.dry_run, limit=args.limit
        )

        if args.resume:
            migration.resume_migration(args.report_dir)
        else:
            migration.run_migration(args.report_dir)

    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        migration.save_progress()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()
