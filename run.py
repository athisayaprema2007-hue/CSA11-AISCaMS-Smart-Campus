"""Development entry point: python run.py"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    print("AISCaMS is starting on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
