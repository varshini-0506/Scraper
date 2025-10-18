from fastapi import FastAPI, Query, HTTPException
from app.amazon_scraper import fast_scrape_amazon_products
from app.flipkart_scraper import scrape_flipkart
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import requests

app = FastAPI(
    title="Amazon & Flipkart Scraper API",
    description="A FastAPI service for scraping product information from Amazon and Flipkart",
    version="1.0.0"
)

@app.get("/")
def root():
    """
    Health check endpoint
    """
    return {
        "message": "Amazon & Flipkart Scraper API is running!",
        "status": "healthy",
        "endpoints": {
            "amazon": "/search/amazon?product={query}&max_results={number}",
            "flipkart": "/search/flipkart?product={query}&max_results={number}",
            "both": "/search/both?product={query}&max_results={number}",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health_check():
    """
    Health check endpoint for monitoring
    """
    return {"status": "healthy", "service": "amazon-flipkart-scraper"}

@app.get("/search/amazon")
def search_amazon(product: str = Query(...), max_results: int = 20):
    """
    Scrapes Amazon for the given product keyword. Returns up to `max_results` results.
    """
    results = fast_scrape_amazon_products(product, max_results)
    
    # Check if the result contains an error
    if isinstance(results, dict) and "error" in results:
        raise HTTPException(status_code=503, detail=results["error"])
    
    return {"results": results}

@app.get("/search/flipkart")
def search_flipkart(product: str, max_results: int = 12):
    try:
        results = scrape_flipkart(product, max_results=max_results)
        return JSONResponse({"results": results})
    except requests.exceptions.RequestException as e:
        # upstream network or remote site error
        print("[route] upstream request error:", e)
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"Upstream fetch failed: {str(e)}")
    except Exception as e:
        print("[route] internal error:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/search/both")
def search_both(product: str = Query(...), max_results: int = 20):
    """
    Scrapes both Amazon and Flipkart for the given product keyword.
    """
    amazon_results = fast_scrape_amazon_products(product, max_results)
    flipkart_results = scrape_flipkart(product, max_results)
    
    # Handle errors
    amazon_data = amazon_results if not isinstance(amazon_results, dict) or "error" not in amazon_results else []
    flipkart_data = flipkart_results if flipkart_results is not None else []
    
    return {
        "amazon": amazon_data,
        "flipkart": flipkart_data,
        "total_amazon": len(amazon_data),
        "total_flipkart": len(flipkart_data)
    }