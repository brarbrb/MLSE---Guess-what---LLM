from flask import jsonify

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error="bad_request", detail=str(e)), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="not_found"), 404

    @app.errorhandler(409)
    def conflict(e):
        return jsonify(error="conflict", detail=str(e)), 409

    @app.errorhandler(500)
    def server_error(e):
        return jsonify(error="server_error"), 500
