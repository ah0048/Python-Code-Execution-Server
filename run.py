import multiprocessing
from app import create_app

if __name__ == '__main__':
    multiprocessing.freeze_support()  # Required for Windows
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
