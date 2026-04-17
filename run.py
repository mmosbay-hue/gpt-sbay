"""Entry point for aaPanel Python Manager / production runner."""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        workers=1,
        log_level="info",
    )
