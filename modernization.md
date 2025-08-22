# Wiki-Guess Modernization

This document outlines the comprehensive modernization work done on the wiki-guess application to bring it up to current Python and web development standards.

## 🚀 **Major Improvements Made**

### 0. **Python 2 (and very old packages) to Python3**

- This was 12-13 years old and focused on deploying to Heroku
- Now it runs (locally, at least) on python 3.9+

### 1. **URL Routing Fixes**

- **Problem**: Forward slashes in URLs like "How.much.would.you.donate.w/.small.text" were breaking Flask routing
- **Solution**: Changed Flask route from `<guess>` to `<path:guess>` to handle forward slashes properly
- **Result**: URLs now work correctly without complex encoding or manual character replacement

### 2. **Image Zoom Functionality**

- **Problem**: `$.colorbox()` jQuery plugin was broken/not working for image zooming
- **Solution**: Replaced with custom CSS modal + vanilla JavaScript

### 3. **S3 Integration & Imgur Migration**

- **Problem**: Screenshots were hosted on Imgur! This had hotlinking issues and reliability concerns
- **Solution**: Complete migration system to AWS S3 with graceful fallback logic
- **Features**:
  - Downloads images from Imgur
  - Uploads to S3 in organized structure (`screenshotsClean/` and `screenshotsImgur/`)
  - Graceful degradation: S3 → Imgur fallback
  - Resume capability and dry-run mode
  - Progress tracking and error handling

### 4. **Project Organization**

- **Problem**: Migration scripts and documentation were scattered in root directory
- **Solution**: Created dedicated `migration/` subfolder
- **Structure**:
  - `migration/imgur_migration.py` - Core migration logic
  - `migration/aws_config.md` - AWS setup instructions
  - `migration/MIGRATION_README.md` - Comprehensive migration guide
  - `migration/test_migration.py` - Testing and validation tools
  - `migration/README.md` - Folder overview

### 5. **Dependency Management**

- **Problem**: Outdated dependencies and manual package management.
- **Solution**:
  - Added `requests>=2.31.0` for HTTP operations
  - Added `pandas>=2.0.0` for CSV processing
  - Moved to `uv`

## 🔧 **Technical Details**

### **Flask Route Changes**

```python
# Before (broken):
@app.route("/show/<batch>/<testname>/result/<guess>")

# After (fixed):
@app.route("/show/<batch>/<testname>/result/<path:guess>")
```

### **S3 Fallback Logic**

```python
# Priority order for screenshot URLs:
# 1. S3 screenshotsClean: s3://wikitoy/screenshotsClean/{testname}/{value}
# 2. S3 screenshotsImgur: s3://wikitoy/screenshotsImgur/{imgur_id}
# 3. Original Imgur URL: http://i.imgur.com/{imgur_id}
```

### **Image Modal Implementation**

- Replaced jQuery Colorbox with vanilla JavaScript
- Custom CSS for responsive modal design
- Keyboard support (Escape to close)
- Click outside to close functionality

## 📁 **File Structure Changes**

```
wiki-guess/
├── migration/                    # NEW: Migration tools and docs
│   ├── imgur_migration.py       # Core migration script
│   ├── aws_config.md            # AWS setup guide
│   ├── MIGRATION_README.md      # Migration documentation
│   ├── test_migration.py        # Testing tools
│   └── README.md                # Folder overview
├── config.example.json          # NEW: Safe config template
├── .gitignore                   # UPDATED: Comprehensive ignore rules
├── README.md                    # UPDATED: Complete documentation
├── pyproject.toml               # UPDATED: New dependencies
├── uv.lock                      # UPDATED: Dependency lock file
├── hello.py                     # UPDATED: Fixed URL routing
├── app_helper.py                # UPDATED: S3 integration
├── templates/base.html          # UPDATED: Image modal CSS
└── templates/guess.html         # UPDATED: Fixed image zoom
```

## 🎯 **Migration System Features**

### **Core Capabilities**

- **CSV Processing**: Handles both dot notation (`extra.screenshot.1`) and underscore notation (`extra_screenshot_1`)
- **S3 Organization**: Two-tier storage system for flexibility
- **Progress Tracking**: Resume capability for long-running migrations
- **Error Handling**: Comprehensive logging and failure recovery
- **Dry Run Mode**: Safe testing without making changes

### **S3 Structure**

```
s3://wikitoy/
├── screenshotsClean/            # Organized by test metadata
│   └── {testname}/
│       └── {optionName}
└── screenshotsImgur/            # Direct Imgur filename mapping
    └── {imgur_id}.{ext}
```
