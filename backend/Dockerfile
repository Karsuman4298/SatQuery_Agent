FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for rasterio/GDAL
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgdal-dev \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip wheel && \
    pip install "setuptools<70.0.0" && \
    pip install --only-binary rasterio --no-cache-dir -r requirements.txt

COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
