"""
 — Entry Point
Run with: python app.py
"""
import uvicorn

if __name__ == "__main__":
    print("\n AI Job Agent starting...")
    print(" Open http://localhost:8000 in your browser\n")
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )