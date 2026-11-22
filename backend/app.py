"""Ponto de entrada do backend PixTáPago (python app.py)."""

from pixtapago import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
