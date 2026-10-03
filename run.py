import sys
import subprocess
import os

def main():
    print("=" * 60)
    print("  FitBuddy AI - Web-Based Workout & Nutrition Planner")
    print("=" * 60)

    # Check if fastapi and uvicorn are available
    try:
        import fastapi
        import uvicorn
        has_fastapi = True
    except ImportError:
        has_fastapi = False

    port = int(os.environ.get("PORT", 8000))

    if has_fastapi:
        print(f"\n[+] FastAPI & Uvicorn detected!")
        print(f"[+] Starting FastAPI server at: http://127.0.0.1:{port}")
        print(f"[+] Interactive Swagger API Docs at: http://127.0.0.1:{port}/docs\n")
        uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
    else:
        print(f"\n[*] Note: FastAPI / Uvicorn not installed in current environment.")
        print(f"[*] Running FitBuddy with built-in zero-dependency server at: http://127.0.0.1:{port}")
        print(f"[*] (Optional) To enable FastAPI & Swagger UI docs, run: pip install -r requirements.txt\n")
        import app_server
        app_server.run(port=port)

if __name__ == "__main__":
    main()
