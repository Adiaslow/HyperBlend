# hyperblend/app/web/app.py
# This file is maintained for backward compatibility

from hyperblend.app.web import create_app

# If this file is executed as a script
if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
