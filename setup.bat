@echo off
cd /d "C:\Users\peter\Desktop\KasKorsou-web"
echo === STAP 1: Vite project aanmaken ===
call npx --yes create-vite@latest temp-init -- --template react
xcopy /E /Y temp-init\* . >nul 2>&1
rmdir /S /Q temp-init
echo === STAP 2: Dependencies installeren ===
call npm install
call npm install @tailwindcss/vite mapbox-gl @supabase/supabase-js lucide-react framer-motion react-router-dom
echo === STAP 3: Dev server starten ===
echo.
echo ==========================================
echo   Open je browser op http://localhost:5173
echo ==========================================
echo.
call npm run dev
