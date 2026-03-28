# ==========================================================
#   Pumping-Test: Python Shiny App
#   Build directly from GitHub
# ==========================================================

FROM python:3.13-slim

# System deps
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Clone the repo directly from GitHub
RUN git clone https://github.com/plosi/pumping-test.git /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Environment variables recommended for Shiny
ENV SHINY_HOST=0.0.0.0
ENV SHINY_PORT=8000

# Expose Shiny's default port
EXPOSE 8000

# Run the Shiny Python app
# Assuming the entry file is named app.py inside the repo
CMD ["shiny", "run", "--host", "0.0.0.0", "--port", "8000", "./app/main.py"]