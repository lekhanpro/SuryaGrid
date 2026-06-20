@echo off
echo ============================================
echo   SURYAGRID AI - Starting Phase 1 System
echo ============================================
echo.

echo [1/2] Starting Backend (port 8000)...
start "SuryaGrid Backend" cmd /k "cd /d D:\Suryagrid AI\backend && uvicorn app.main:app --reload --port 8000"

echo [2/2] Starting Frontend (port 3000)...
start "SuryaGrid Frontend" cmd /k "cd /d D:\Suryagrid AI\frontend && npm run dev"

echo.
echo ============================================
echo   Both servers starting in new windows!
echo.
echo   Backend:  http://localhost:8000/docs
echo   Frontend: http://localhost:3000
echo   Dashboard: http://localhost:3000/dashboard
echo ============================================
echo.
timeout /t 5 >nul
start http://localhost:3000/dashboard
