print("Performing imports")
from flask import Flask, request, jsonify, send_file
print("Performing Torch")
import torch
from torchvision import transforms
from PIL import Image
import sys
import os
import logging
import time
from prometheus_client import start_http_server, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

logging.info("Import Fast Neural..")
sys.path.append('./examples/fast_neural_style/')
from neural_style.transformer_net import TransformerNet

# Initialize Flask app
logging.info("Initialize Flask app...")
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load the pre-trained model
logging.info("Loading pre-trained model...")
model = TransformerNet()

# Load the state dictionary and remove unnecessary keys
state_dict = torch.load("./mosaic.pth")
keys_to_remove = [key for key in state_dict.keys() if "running_mean" in key or "running_var" in key]
for key in keys_to_remove:
    del state_dict[key]

# Load the modified state dictionary into the model
model.load_state_dict(state_dict)
model.eval()
logging.info("Model loaded successfully!")

# Define image transformation
def transform_image(image_path):
    logging.info("Transforming input image...")
    transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.ToTensor(),
        transforms.Lambda(lambda x: x.mul(255))
    ])
    image = Image.open(image_path).convert('RGB')
    return transform(image).unsqueeze(0)

# Prometheus metrics
REQUESTS = Counter('flask_requests_total', 'Total number of requests', ['endpoint', 'status_code'])
REQUEST_LATENCY = Histogram('flask_request_duration_seconds', 'Request latency in seconds', ['endpoint'])
REQUEST_RATE = Counter('flask_requests_rate', 'Request rate per second', ['endpoint'])

# Expose /metrics endpoint with correct content type
@app.route('/metrics')
def metrics():
    # Generate the latest metrics and return with the correct content-type header
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/styleTransfer', methods=['POST'])
def style_transfer():
    logging.info("Received a request for style transfer.")
    start_time = time.time()  # Start time for tracking latency

    # Check if image is uploaded
    if 'image' not in request.files:
        logging.warning("No image uploaded in the request.")
        REQUESTS.labels(endpoint='/styleTransfer', status_code='400').inc()  # Increment counter for 400 status
        return jsonify({"error": "No image uploaded"}), 400

    image_file = request.files['image']
    input_path = "input.jpg"
    output_path = "output.jpg"

    # Save the uploaded image
    logging.info("Saving uploaded image...")
    image_file.save(input_path)
    logging.info(f"Image saved as {input_path}.")

    # Transform and stylize the image
    try:
        logging.info("Applying style transfer...")
        input_image = transform_image(input_path)
        with torch.no_grad():
            output_image = model(input_image).squeeze(0)
        output_image = transforms.ToPILImage()(output_image / 255.0)
        output_image.save(output_path)
        logging.info(f"Styled image saved as {output_path}.")
    except Exception as e:
        logging.error(f"Error during style transfer: {e}")
        REQUESTS.labels(endpoint='/styleTransfer', status_code='500').inc()  # Increment counter for 500 status
        return jsonify({"error": "Style transfer failed", "details": str(e)}), 500

    # Measure response time and increment success request counter
    response_time = time.time() - start_time
    REQUEST_LATENCY.labels(endpoint='/styleTransfer').observe(response_time)  # Track latency
    REQUESTS.labels(endpoint='/styleTransfer', status_code='200').inc()  # Increment counter for 200 status
    REQUEST_RATE.labels(endpoint='/styleTransfer').inc()  # Increment the rate counter

    # Return the styled image
    logging.info("Sending styled image to client.")
    return send_file(output_path, mimetype='image/jpeg')

if __name__ == "__main__":
    logging.info("Starting Flask server...")
    
    # Start Prometheus server to expose metrics at /metrics
    start_http_server(8000)  # Exposing metrics on port 8000
    
    app.run(host='0.0.0.0', port=5001)
