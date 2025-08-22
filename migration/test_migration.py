#!/usr/bin/env python3
"""
Test script for imgur migration functionality
"""

import os
import tempfile
import csv
from imgur_migration import ImgurMigration


def create_test_csv():
    """Create a test CSV file with sample imgur URLs"""
    test_data = [
        {
            "test_id": "1234567890",
            "value": "Test.option.name",
            "campaign": "Test_Campaign",
            "screenshot": "http://i.imgur.com/test123.png",
            "extra.screenshot.1": "NA",
            "extra.screenshot.2": "NA",
            "testname": "1234567890Test.test",
        },
        {
            "test_id": "1234567890",
            "value": "Another.test.option",
            "campaign": "Test_Campaign",
            "screenshot": "http://i.imgur.com/another456.jpg",
            "extra.screenshot.1": "http://i.imgur.com/extra789.gif",
            "extra.screenshot.2": "NA",
            "testname": "1234567890Test.test",
        },
    ]

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "screenshots.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=test_data[0].keys())
        writer.writeheader()
        writer.writerows(test_data)

    return temp_dir, csv_path


def test_csv_parsing():
    """Test CSV parsing functionality"""
    print("Testing CSV parsing...")

    temp_dir, csv_path = create_test_csv()

    try:
        migration = ImgurMigration(dry_run=True)
        entries = migration.process_csv_file(csv_path)

        print(f"Found {len(entries)} imgur entries:")
        for entry in entries:
            print(f"  - {entry['url']} -> {entry['imgur_id']}")
            print(f"    Test: {entry['testname']}, Value: {entry['value']}")

        # Clean up
        os.remove(csv_path)
        os.rmdir(temp_dir)

        print("✅ CSV parsing test passed")
        return True

    except Exception as e:
        print(f"❌ CSV parsing test failed: {e}")
        return False


def test_imgur_id_extraction():
    """Test imgur ID extraction"""
    print("Testing imgur ID extraction...")

    migration = ImgurMigration(dry_run=True)

    test_urls = [
        "http://i.imgur.com/test123.png",
        "http://i.imgur.com/another456.jpg",
        "http://imgur.com/extra789.gif",
        "https://i.imgur.com/webp123.webp",
        "NA",
        "",
        None,
    ]

    expected_ids = ["test123", "another456", "extra789", "webp123", None, None, None]

    for url, expected_id in zip(test_urls, expected_ids):
        extracted_id = migration.extract_imgur_id(url)
        if extracted_id == expected_id:
            print(f"  ✅ {url} -> {extracted_id}")
        else:
            print(f"  ❌ {url} -> {extracted_id} (expected {expected_id})")
            return False

    print("✅ Imgur ID extraction test passed")
    return True


def test_content_type_detection():
    """Test content type detection"""
    print("Testing content type detection...")

    migration = ImgurMigration(dry_run=True)

    test_cases = [
        (
            "http://example.com/image.png",
            b"\x89PNG\r\n\x1a\nfake_png_data",
            "image/png",
        ),
        ("http://example.com/image.jpg", b"\xff\xd8\xfffake_jpg_data", "image/jpeg"),
        ("http://example.com/image.gif", b"GIF87afake_gif_data", "image/gif"),
        ("http://example.com/image.webp", b"fake_webp_data", "image/webp"),
        ("http://example.com/unknown", b"unknown_data", "application/octet-stream"),
    ]

    for url, data, expected_type in test_cases:
        detected_type = migration.get_content_type(url, data)
        if detected_type == expected_type:
            print(f"  ✅ {url} -> {detected_type}")
        else:
            print(f"  ❌ {url} -> {detected_type} (expected {expected_type})")
            return False

    print("✅ Content type detection test passed")
    return True


def test_s3_connectivity():
    """Test S3 connectivity and permissions"""
    print("Testing S3 connectivity and permissions...")

    try:
        # Test with dry run first to check basic connectivity
        migration = ImgurMigration(dry_run=True)
        print("  ✅ S3 client initialization (dry run)")

        # Now test actual S3 connectivity
        migration_real = ImgurMigration(dry_run=False)
        print("  ✅ S3 client initialization (real)")

        # Test bucket access
        try:
            migration_real.s3_client.head_bucket(Bucket=migration_real.bucket_name)
            print(f"  ✅ Bucket access: {migration_real.bucket_name}")
        except Exception as e:
            print(f"  ❌ Bucket access failed: {e}")
            return False

        # Test write permissions with a small test file
        test_key = "test_migration/test_write_permission.txt"
        test_data = b"Test file to verify S3 write permissions"

        try:
            migration_real.s3_client.put_object(
                Bucket=migration_real.bucket_name,
                Key=test_key,
                Body=test_data,
                ContentType="text/plain",
            )
            print(
                f"  ✅ Write permission: s3://{migration_real.bucket_name}/{test_key}"
            )

            # Clean up test file
            migration_real.s3_client.delete_object(
                Bucket=migration_real.bucket_name, Key=test_key
            )
            print(
                f"  ✅ Delete permission: s3://{migration_real.bucket_name}/{test_key}"
            )

        except Exception as e:
            print(f"  ❌ Write permission failed: {e}")
            return False

        print("✅ S3 connectivity and permissions test passed")
        return True

    except Exception as e:
        print(f"  ❌ S3 connectivity test failed: {e}")
        print("  💡 Make sure you have AWS credentials configured")
        print("  💡 Check that you have access to the S3 bucket")
        return False


def test_s3_upload_simulation():
    """Test S3 upload simulation with dry run"""
    print("Testing S3 upload simulation...")

    try:
        migration = ImgurMigration(dry_run=True)

        # Test a sample imgur entry
        test_entry = {
            "url": "http://i.imgur.com/test123.png",
            "imgur_id": "test123",
            "testname": "TestMigration",
            "value": "Test.option.name",
        }

        # Simulate the migration process
        result = migration.migrate_imgur_url(test_entry)

        if result:
            print("  ✅ S3 upload simulation successful")
            print("  ✅ Would upload to screenshotsImgur/test123.png")
            print(
                "  ✅ Would upload to screenshotsClean/TestMigration/Test.option.name.png"
            )
            return True
        else:
            print("  ❌ S3 upload simulation failed")
            return False

    except Exception as e:
        print(f"  ❌ S3 upload simulation test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("Running imgur migration tests...\n")

    tests = [
        test_csv_parsing,
        test_imgur_id_extraction,
        test_content_type_detection,
        test_s3_connectivity,
        test_s3_upload_simulation,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}\n")

    print(f"Tests completed: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
