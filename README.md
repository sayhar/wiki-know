# Wiki-Guess

A Flask web application for displaying and analyzing A/B test results with screenshots, statistical data, and user guessing functionality.

## Features

- **Test Results Display**: Shows test results with screenshots and statistical information
- **User Interaction**: Allows users to guess which variation performed better
- **Multiple Viewing Modes**: Supports GUESS/NOGUESS modes (we default to GUESS mode)
- **Flexible Organization**: Can organize tests by various criteria (chronological, reverse chronological)
- **Performance Optimized**: Cached directory views and parallel processing for large test sets

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configuration

Copy the example configuration and customize it:

```bash
cp config.example.json config.json
```

Edit `config.json` with your settings:

```json
{
  "bucketname": "your-s3-bucket-name",
  "basicauth_name": "username",
  "basicauth_password": "password",
  "mode": "GUESS",
  "interesting_tests": ["test1", "test2", "test3"]
}
```

**Note**: S3 and authentication are optional for local development.

### 3. Run the Application

```bash
uv run hello.py
```

The app will be available at `http://127.0.0.1:5000`

## Test Data Format

This application relies on data being in a standard format in directories. Each test should be in its own directory under `static/report/`.

### Required Files

Each test directory must contain:

- **`meta.csv`** - Test results and statistical data
- **`screenshots.csv`** - Screenshot URLs and test variations

### Optional Files

- **`val_lookup.csv`** - Human-readable names for test variations
- **`description.txt`** - Test description (supports HTML)
- **`reportA.html`** - Detailed results table for variation A
- **`reportB.html`** - Detailed results table for variation B
- **`pamplona.png`** - Main confidence chart over time
- **Additional PNG files** - Extra screenshots as needed

### File Format Specifications

#### meta.csv

- Must be a 2-line CSV file
- Each row must have at least 10 fields
- **Row 4**: Winner variation name (must match val_lookup.csv and screenshots.csv)
- **Row 5**: Loser variation name (must match val_lookup.csv and screenshots.csv)
- **Row 6**: Naive percentage winning amount
- **Row 8**: Upper bound of confidence interval
- **Row 9**: Lower bound of confidence interval

Example:

```csv
"test_id","var","country","language","winner","loser","bestguess","p","lowerbound","upperbound","totalimpressions","totaldonations"
"1366565886","Banner.design","YY","yy","Key.phrase.in.blue","All.text.in.black",2.69,0.018,0.46,4.92,95076500,31750
```

#### screenshots.csv

- First line contains column names (ignored)
- Each row must have at least 4 fields
- **Row 1**: Test ID
- **Row 2**: Variation name (must match meta.csv winner/loser and val_lookup.csv)
- **Row 3**: Campaign name
- **Row 4**: Direct URL to screenshot image
- **Rows 5-6**: Optional extra screenshots (currently unused)

Example:

```csv
"test_id","value","campaign","screenshot","extra.screenshot.1","extra.screenshot.2","testname"
"1366565886","Key.phrase.in.blue","C13_wpnd_enWW_FR","http://i.imgur.com/32wJUQD.png",NA,NA,"1366565886Banner.design"
"1366565886","All.text.in.black","C13_wpnd_enWW_FR","http://i.imgur.com/QW0FDGU.png",NA,NA,"1366565886Banner.design"
```

#### val_lookup.csv

- First row is skipped
- **Column A**: Canonical internal name (must match meta.csv and screenshots.csv)
- **Column B**: Human-readable display name

Example:

```csv
"value","description"
"Key.phrase.in.blue","Key phrase in blue"
"All.text.in.black","All text in black"
```

#### description.txt

- Plain text description of the test
- HTML formatting is supported
- Users will see this description

#### reportA.html / reportB.html

- Must contain only a table
- Should have classes: `"table table-hover table-bordered"`
- Include interesting data about the test

#### pamplona.png

- Main chart showing confidence in the test over time
- Gets prominent display in the report

## Configuration

The application uses `config.json` for configuration. For local development, you can create a minimal config:

```json
{
  "mode": "GUESS"
}
```

### Configuration Options

- **`mode`**: Application mode ("GUESS" or "NOGUESS")
- **`bucketname`**: S3 bucket name for remote storage
- **`basicauth_name`**: Username for BasicAuth
- **`basicauth_password`**: Password for BasicAuth
- **`interesting_tests`**: List of test IDs to highlight in the interface

## Development

### Project Structure

- **`hello.py`** - Main Flask application
- **`app_helper.py`** - Core logic for test data and caching
- **`app_functions.py`** - Functions for displaying test results
- **`config.json`** - Application configuration
- **`static/`** - Static assets and test reports
- **`static-archive/`** - Archived tests (gitignored)

### Key Features

- **Caching**: Intelligent caching for directory views to improve performance
- **Parallel Processing**: Uses ThreadPoolExecutor for faster file I/O
- **Archive Management**: Keeps only active tests in main directory for performance
- **Modern Python**: Built with Python 3 and modern Flask practices

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed with `uv sync`
2. **File Not Found**: Check that the `static/report/` directory structure exists
3. **S3 Errors**: The app works without S3 - check console for warnings
4. **Auth Errors**: Basic auth is optional and can be disabled
5. **Slow Directory Views**: Check that caching is working and tests are properly archived

### Performance Notes

- Large test sets (>1000 tests) should be archived to `static-archive/`
- The app automatically caches processed directory data
- Only "chronological" and "reverse" batch types are supported for optimal performance

## Modernization Notes

This application has been significantly modernized from its original 2012-2013 codebase. While the core functionality remains valuable, the original design reflects different engineering practices and constraints of that era.

### Design Decisions & Constraints

(Some decisions to internal constraints and data processing workflows not worth getting into)

- **CSV over JSON**: The application uses CSV files. JSON would be better.

- **Flat File Storage**: Much of the data that would today be stored in a proper database (like SQLite) is stored in flat files. This reflects both the original deployment constraints and the need for simple, portable data structures.

- **Legacy Visualization**: Charts and graphs use older libraries (like lattice) rather than modern alternatives. The focus was on functionality over visual polish.

- **Mixed Polish Level**: The codebase exists in a state between internal tool and public application - some parts are polished for external use, while others retain the practical but less polished approach typical of internal tools.

### What's Been Modernized

- **Python 3**: Updated from Python 2 to Python 3.9+
- **Modern Flask**: Updated routing patterns and best practices
- **Dependency Management**: Moved to `uv` and modern package management
- **Performance**: Added caching, parallel processing, and archive management
- **Code Quality**: Improved error handling and modern Python patterns

### What Remains Legacy

- **Data Format**: CSV-based data structure remains largely unchanged
- **File Organization**: Directory-based test storage system
- **Visualization**: Basic chart rendering without modern chart libraries
- **Code quality**: Not the best!

## License

This is a modernized version of the original wiki-guess application, updated for Python 3 and modern Flask practices.
