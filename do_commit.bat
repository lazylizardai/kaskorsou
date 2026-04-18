@echo off
cd /d C:\Users\peter\Desktop\KasKorsou-web
git config user.email "phmarketeer@gmail.com"
git config user.name "Peter"
git add .
git commit -m "Initial KasKorsou frontend"
git log --oneline
echo EXIT_CODE=%ERRORLEVEL%
