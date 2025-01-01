import requests
import time

# Define the URL for the POST request
url = "http://localhost:5001/styleTransfer"

# Time duration for making requests (in seconds)
duration = 60  # 1 minute

# Start time for the 1-minute loop
start_time = time.time()

# Loop for 1 minute (60 seconds)
while time.time() - start_time < duration:
    # Open an image file to send as part of the POST request
    with open("carlsen.jpg", "rb") as image_file:
        # Send the POST request with the image
        files = {'image': image_file}
        response = requests.post(url, files=files)

    # Print the response status and message (optional)
    print(f"Response Status Code: {response.status_code}, Response Body: {response.text}")

    # Wait for a short time before sending the next request
    # You can adjust the time between requests as needed, e.g., 1 second
    time.sleep(1)  # wait 1 second before sending the next request
