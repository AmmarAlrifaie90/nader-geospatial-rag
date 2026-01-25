# 🚀 GitHub Upload Guide for NADER Project

## Step 1: Verify Sensitive Files Are Protected

Before uploading, make sure:

1. ✅ `.env` file is in `.gitignore` (already done)
2. ✅ All API keys, passwords, and credentials are in `.env` (not hardcoded)
3. ✅ ML model files (`.pkl`) are excluded (optional - you can include them if they're not too large)
4. ✅ No service account JSON files are in the repo

## Step 2: Initialize Git Repository

Open PowerShell in your project directory:

```powershell
cd c:\Users\ammar\Desktop\geospatial-rag\backpoly\geospatial-rag

# Initialize git (if not already done)
git init

# Check what will be committed
git status
```

## Step 3: Add Files to Git

```powershell
# Add all files (respecting .gitignore)
git add .

# Check what's staged
git status
```

**Important:** Verify that `.env` and sensitive files are NOT listed!

## Step 4: Create Initial Commit

```powershell
git commit -m "Initial commit: NADER Geospatial RAG System"
```

## Step 5: Create GitHub Repository

1. Go to [GitHub.com](https://github.com)
2. Click **"New repository"** (or the **+** icon)
3. Repository name: `nader-geospatial-rag` (or your preferred name)
4. Description: "NADER - Geospatial RAG System for Mining Database Query and Analysis"
5. Choose **Public** or **Private**
6. **DO NOT** initialize with README, .gitignore, or license (we already have these)
7. Click **"Create repository"**

## Step 6: Connect Local Repository to GitHub

After creating the repository, GitHub will show you commands. Use these:

```powershell
# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/nader-geospatial-rag.git

# Rename main branch (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

## Step 7: Verify Upload

1. Go to your GitHub repository page
2. Check that:
   - ✅ `.env` file is **NOT** visible
   - ✅ `.gitignore` is present
   - ✅ All code files are uploaded
   - ✅ README.md is visible

## Step 8: Add Repository Description

On GitHub, add:
- **Description:** "NADER - Geospatial RAG System with Natural Language Query, Spatial Analysis, and ML Prediction"
- **Topics:** `rag`, `geospatial`, `postgis`, `ollama`, `fastapi`, `spatial-analysis`, `mining-database`, `agentic-ai`

## Step 9: Update README with Setup Instructions

Make sure your README includes:
- How to set up `.env` file
- Required environment variables
- Database setup instructions
- How to get API keys (without exposing your keys)

## 🔒 Security Checklist

Before pushing, verify:

- [ ] `.env` file is in `.gitignore`
- [ ] No passwords in code files
- [ ] No API keys hardcoded
- [ ] No database credentials in code
- [ ] No service account JSON files
- [ ] `.env.example` exists with placeholder values
- [ ] README explains how to set up environment variables

## 📝 What Gets Uploaded

✅ **Included:**
- All Python code
- Frontend HTML/CSS/JS
- Configuration files (`.env.example`)
- Documentation (README, guides)
- `.gitignore`
- Requirements files

❌ **Excluded (by .gitignore):**
- `.env` (secrets)
- `__pycache__/` (Python cache)
- `*.pkl` (ML models - optional, you can include if small)
- `exports/` (user data)
- `*.log` (logs)
- IDE files (`.vscode/`, `.idea/`)
- OS files (`.DS_Store`, `Thumbs.db`)

## 🎯 Optional: Include ML Models

If your ML models are small (< 50MB each), you can include them:

1. Remove `*.pkl` from `.gitignore`
2. Or add specific model files:
   ```gitignore
   # Exclude all .pkl except specific ones
   *.pkl
   !ml/prospectivity_model.pkl
   !ml/prospectivity_scaler.pkl
   ```

## 📦 Large Files (> 100MB)

If you have large files:
- Use [Git LFS](https://git-lfs.github.com/) for ML models
- Or host models separately and download in setup script

## 🔄 Future Updates

To push future changes:

```powershell
git add .
git commit -m "Description of changes"
git push
```

## 🆘 Troubleshooting

**"Remote origin already exists"**
```powershell
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/nader-geospatial-rag.git
```

**"Large file detected"**
- Use Git LFS or remove large files from history

**"Authentication failed"**
- Use GitHub Personal Access Token instead of password
- Or use SSH keys
