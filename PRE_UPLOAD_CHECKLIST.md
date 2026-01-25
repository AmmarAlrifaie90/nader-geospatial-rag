# ✅ Pre-Upload Security Checklist

Before uploading to GitHub, verify the following:

## 🔒 Security Checks

- [ ] **`.env` file exists and is NOT tracked by git**
  - Run: `git status` - `.env` should NOT appear
  - If it appears, run: `git rm --cached backend/.env`

- [ ] **No hardcoded passwords in code**
  - All credentials loaded from `.env` file
  - Default values in `config.py` are safe (they're just defaults)

- [ ] **No API keys in code**
  - Mapbox token: Set via Settings UI (stored in localStorage)
  - Google Cloud: Loaded from `.env` file
  - All API keys use environment variables

- [ ] **No service account JSON files**
  - Check: `git status` should not show any `*credentials*.json` or `*service-account*.json`
  - If found: Add to `.gitignore` and remove from git: `git rm --cached path/to/file.json`

- [ ] **`.env.example` exists with placeholders**
  - Contains all required variables
  - Uses placeholder values like `your_password_here`
  - No real credentials

## 📁 File Checks

- [ ] **`.gitignore` is present and complete**
  - Excludes `.env`
  - Excludes `__pycache__/`
  - Excludes `*.pkl` (ML models)
  - Excludes `exports/` directory
  - Excludes logs and temporary files

- [ ] **No large files (> 100MB)**
  - ML models (`.pkl`) are excluded
  - If you want to include models, use Git LFS

- [ ] **No user data in exports/**
  - Exports directory is in `.gitignore`
  - No personal data will be uploaded

## 📝 Documentation Checks

- [ ] **README.md is updated**
  - Explains how to set up `.env` file
  - Lists required environment variables
  - No real credentials in examples

- [ ] **Setup instructions are clear**
  - Users know to copy `.env.example` to `.env`
  - Instructions for getting API keys (without exposing yours)

## 🧪 Test Before Upload

1. **Clone to a test directory:**
   ```powershell
   cd C:\temp
   git clone <your-repo-url> test-clone
   cd test-clone
   ```

2. **Verify sensitive files are missing:**
   - `.env` should NOT exist
   - No credentials files

3. **Verify code still works:**
   - Follow setup instructions
   - Create `.env` from `.env.example`
   - Test that application runs

## 🚨 If You Accidentally Committed Secrets

**If you already pushed secrets to GitHub:**

1. **Remove from git history:**
   ```powershell
   git filter-branch --force --index-filter "git rm --cached --ignore-unmatch backend/.env" --prune-empty --tag-name-filter cat -- --all
   ```

2. **Force push (WARNING: This rewrites history):**
   ```powershell
   git push origin --force --all
   ```

3. **Rotate all exposed credentials:**
   - Change database passwords
   - Regenerate API keys
   - Create new service account keys

## ✅ Final Verification

Run these commands before pushing:

```powershell
# Check what will be committed
git status

# Verify .env is ignored
git check-ignore backend/.env
# Should output: backend/.env

# List all files that will be committed
git ls-files

# Verify no secrets in tracked files
git grep -i "password\|api_key\|secret" -- "*.py" "*.js" "*.html"
# Should only show default values or comments
```

## 🎯 Ready to Upload?

If all checks pass, proceed with:

```powershell
git add .
git commit -m "Initial commit: NADER Geospatial RAG System"
git push -u origin main
```
