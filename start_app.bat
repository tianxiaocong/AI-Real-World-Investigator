@echo off
echo Starting AI Real-World Investigator Backend...
call .\.venv\Scripts\activate
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
