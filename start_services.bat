@echo off
echo Starting Flask app...
start cmd /k "C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe app.py"

echo Starting Word Generator...
timeout /t 3
start cmd /k "C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe -m uvicorn word_generator_agent:app --reload --port 8000"

echo Both services started!