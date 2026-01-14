"""
Entry point for analytics service
Can run as standalone service or be imported as module
"""

from flask import Flask, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "analytics"})


@app.route('/simulator/calculate', methods=['POST'])
def calculate_gravity():
    """Calculate gravity vector"""
    # TODO: Implement endpoint
    return jsonify({"error": "Not implemented"})


if __name__ == '__main__':
    logger.info("Starting analytics service...")
    app.run(host='localhost', port=5000, debug=True)
