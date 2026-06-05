# The recipe Hugging Face uses to run your backend Space (Docker SDK).
# Hugging Face Spaces expect the app to listen on port 7860.
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so this layer caches between code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then the code.
COPY . .

EXPOSE 7860

# Start the server. main:app = the `app` object inside main.py.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
