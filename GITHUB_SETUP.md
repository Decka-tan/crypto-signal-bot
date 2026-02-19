# GitHub Setup - Connect Your Repo

## Step 1: Create GitHub Repository

1. Go to: https://github.com/new
2. Repository name: `crypto-signal-bot`
3. Description: `Crypto trading bot with AI-powered technical analysis`
4. Public or Private (your choice)
5. ❌ DON'T check "Initialize with README"
6. Click **Create repository**

## Step 2: Connect Local Repo to GitHub

After creating, GitHub will show commands. Run these:

### Option A: HTTPS (Easier)
```bash
cd crypto-signal-bot

# Add your GitHub repo URL
git remote add origin https://github.com/YOUR_USERNAME/crypto-signal-bot.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Option B: SSH (If you have SSH keys setup)
```bash
cd crypto-signal-bot

git remote add origin git@github.com:YOUR_USERNAME/crypto-signal-bot.git
git branch -M main
git push -u origin main
```

## Step 3: Verify

Go to your GitHub repo - you should see all the files!

---

## Update GitHub Identity (Optional)

If you want to use your own name/email:

```bash
git config --global user.name "YOUR NAME"
git config --global user.email "your.email@example.com"

# Update last commit (optional)
git commit --amend --reset-author --no-edit
git push -f origin main
```

---

## Future Commits

```bash
# Make changes
# ...

# Add changes
git add .

# Commit
git commit -m "Your commit message"

# Push
git push
```

---

## Farm Commits for Activity Graph

Want to build your GitHub contribution graph?

```bash
# Make small changes regularly
git commit --allow-empty -m "Daily update $(date +%Y-%m-%d)"
git push
```

Or create a script to auto-commit daily!

---

Your repo is ready to push! 🚀
