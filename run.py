from flask_app import app

if __name__ == "__main__":
    # Para desarrollo: app.run(debug=True, host='0.0.0.0', port=5000)
    # Para testing inicial sin problemas de recarga: app.run(debug=False, host='0.0.0.0', port=5000)
    app.run(debug=False, host='0.0.0.0', port=5000)
