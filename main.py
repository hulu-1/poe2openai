from app import create_app
from app.config import PORT

app = create_app()

if __name__ == '__main__':
    import uvicorn
    port = int(PORT)
    uvicorn.run("main:app", host='0.0.0.0', port=port, reload=True)
