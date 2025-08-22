# Wiki-Guess - Modernized

This is a modernized version of the original wiki-guess application, updated for Python 3 and modern Flask practices.

## Installation

### Minimal Installation (Local Development)

```bash
pip install -r requirements-minimal.txt
```

### Full Installation (Production with S3)

```bash
pip install -r requirements.txt
```

## Running the Application

### Basic Test

First, test that the modernized code works:

```bash
python3 test_basic.py
```

### Run the Flask App

```bash
python3 hello.py
```

The application will be available at `http://localhost:5000`

## Configuration

The application uses `config.json` for configuration. For local development, you can create a minimal config:

```json
{
  "mode": "GUESS"
}
```

## Key Changes Made

1. **Removed Python 2 Dependencies**: All Python 2 specific code has been updated
2. **Modern Flask**: Updated to use current Flask patterns and best practices
3. **Better Error Handling**: Specific exception handling instead of generic catches
4. **Optional Dependencies**: S3 and authentication are now optional for easier local development
5. **Code Standards**: Follows modern Python coding standards and conventions

## What This Application Does

- Shows test results with screenshots
- Allows users to guess which variation performed better
- Displays statistical information about test performance
- Supports different viewing modes (GUESS/NOGUESS)
- Can organize tests by various criteria (chronological, random, etc.)

Right now, it's configured in a bittle way for the output of wiki-crunch.

## Adding your own tests:

### This app relies on data being in a standard format in directories.

### Here are the assumptions:

1. Each test is found in it's on directory in static/reports/
2. In each test's directory, there must be at least the following files (formatted correctly):
   - meta.csv
   - screenshots.csv
3. In each tests directory, there should be the following files (formatted correctly):
   - val_lookup.csv
   - description.txt
   - reportA.html
   - reportB.html
   - pamplona.png
4. In each tests directory there can be as many png files as you want.

## Development Notes

- The application expects data files in `static/report/` directories
- Each test should have a `meta.csv` file with test results
- Screenshots are referenced in `screenshots.csv` files
- The app can work with or without S3 storage
- Authentication is optional and can be disabled for local development

## Troubleshooting

## Troubleshooting -- right now we have brittle assumptions!

If you encounter issues:

1. **Import Errors**: Make sure you have the required packages installed
2. **File Not Found**: Check that the `static/report/` directory structure exists
3. **S3 Errors**: The app will work without S3 - check the console for warnings
4. **Auth Errors**: Basic auth is optional and can be disabled

### B. How to format _screenshots.csv_:

#### Things that have no room for error:

1. screenshots.csv's top line is assumed to be column names and is ignored
2. each row must have at least 4 fields
3. row[3] must be a direct URL to the relevant screenshot image
4. row[1] must be the name of the value to be tested. This should be identical to "winner" or "loser" in meta.csv and 'value' in val_lookup.csv
   ####Assumptions:
5. fields 5 and 6 are for alternate screenshots. (currently not used)
6. There will be only 2 different values. (Multiples with the same name are fine).

#### The model _screenshots.csv_ might look like this:

"test*id","value","campaign","screenshot","extra.screenshot.1","extra.screenshot.2","testname"
"1366565886","Key.phrase.in.blue","C13_wpnd_enWW_FR","http://i.imgur.com/32wJUQD.png",NA,NA,"1366565886Banner.design"
"1366565886","All.text.in.black","C13_wpnd_enWW_FR","http://i.imgur.com/QW0FDGU.png",NA,NA,"1366565886Banner.design"
###C. How to format \_val_lookup.csv*

1. First row is skipped
2. Column A is the canonical internal name of the thing being tested. Should be the same as in screenshots.csv and as "winner" or "loser" in meta.csv
3. Column B is the text you want to display to the user as the name of the banner being tested.
   ####The model _val_lookup.csv_ looks like this:
   "value","description"
   "Key.phrase.in.blue","Key phrase in blue"
   "All.text.in.black","All text in black"
   ###D. How to format _description.txt_
   Write in plain text (html works too) the description of what's going on in the test. Users will see it.
   ###E. How to format _reportA.html_
4. ReportA.html should contain a table, and only a table.
5. It should have these classes: "table table-hover table-bordered"
6. reportA should include interesting data about the test
   ###F. How to format _reportB.html_
   _see report A_
   ###G. What is pamplona.png?
   It is the main chart you use to show your confidence in the test over time. It gets pride-of-the-place treatment in the report.
