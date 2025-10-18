#!/usr/bin/env python3
"""
Test script for Flipkart scraper deployment
"""
import requests
import time

def test_flipkart_api():
    """Test the Flipkart API endpoint"""
    base_url = "https://your-render-app.onrender.com"  # Replace with your actual Render URL
    
    print("🧪 Testing Flipkart API...")
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"✅ Health check: {response.status_code}")
        print(f"📄 Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return
    
    # Test 2: Flipkart search
    try:
        print("\n🔍 Testing Flipkart search...")
        response = requests.get(f"{base_url}/search/flipkart?product=iphone&max_results=3", timeout=30)
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Found {len(data.get('results', []))} products")
            if data.get('results'):
                print(f"📱 Sample product: {data['results'][0].get('title', 'No title')}")
        else:
            print(f"❌ Error: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out - this is expected for Flipkart due to rate limiting")
    except Exception as e:
        print(f"❌ Flipkart test failed: {e}")

if __name__ == "__main__":
    test_flipkart_api()
