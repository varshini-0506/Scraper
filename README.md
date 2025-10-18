# Amazon & Flipkart Scraper API

A FastAPI-based web scraping service that extracts product information from Amazon and Flipkart.

## Features

- **Amazon Scraper**: Extracts product details from Amazon India
- **Flipkart Scraper**: Extracts product details from Flipkart
- **Combined Search**: Search both platforms simultaneously
- **Anti-blocking**: User-agent rotation, session management, and retry strategies
- **Fast Performance**: Optimized for speed with timeout controls

## API Endpoints

### Amazon Search
```
GET /search/amazon?product={query}&max_results={number}
```

### Flipkart Search
```
GET /search/flipkart?product={query}&max_results={number}
```

### Combined Search
```
GET /search/both?product={query}&max_results={number}
```

## Example Usage

```bash
# Search Amazon for laptops
curl "https://your-app.onrender.com/search/amazon?product=laptop&max_results=5"

# Search Flipkart for phones
curl "https://your-app.onrender.com/search/flipkart?product=iphone&max_results=5"

# Search both platforms
curl "https://your-app.onrender.com/search/both?product=sunscreen&max_results=3"
```

## Response Format

```json
{
  "results": [
    {
      "id": "product_id",
      "title": "Product Name",
      "link": "https://product-url.com",
      "image": "https://image-url.com",
      "price": "₹1,999",
      "rating": "4.5"
    }
  ]
}
```

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
uvicorn app.main:app --reload
```

3. Access the API at `http://localhost:8000`

## Deployment

This project is configured for deployment on Render.com with the included `render.yaml` file.
