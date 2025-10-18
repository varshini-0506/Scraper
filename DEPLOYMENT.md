# Deployment Guide for Render.com

## Prerequisites
1. GitHub account
2. Render.com account (free tier available)
3. Your code pushed to a GitHub repository

## Step-by-Step Deployment

### 1. Push Your Code to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/your-repo-name.git
git push -u origin main
```

### 2. Deploy to Render

1. **Go to [Render.com](https://render.com)** and sign up/login
2. **Click "New +"** → **"Web Service"**
3. **Connect your GitHub repository**
4. **Configure the service:**

   **Basic Settings:**
   - **Name**: `amazon-scraper-api` (or your preferred name)
   - **Environment**: `Python 3`
   - **Region**: Choose closest to your users
   - **Branch**: `main`

   **Build & Deploy:**
   - **Build Command**: `pip install -r requirements.txt && playwright install chromium`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

   **Advanced Settings:**
   - **Python Version**: `3.9.0`
   - **Auto-Deploy**: `Yes` (optional)

5. **Click "Create Web Service"**

### 3. Environment Variables (Optional)
If you need any environment variables, add them in the Render dashboard under "Environment".

### 4. Wait for Deployment
- First deployment takes 5-10 minutes
- Subsequent deployments are faster
- You'll get a URL like: `https://your-app-name.onrender.com`

## Testing Your Deployment

Once deployed, test your API:

```bash
# Test Amazon scraper
curl "https://your-app-name.onrender.com/search/amazon?product=laptop&max_results=3"

# Test Flipkart scraper  
curl "https://your-app-name.onrender.com/search/flipkart?product=iphone&max_results=3"

# Test combined search
curl "https://your-app-name.onrender.com/search/both?product=sunscreen&max_results=2"
```

## Important Notes

### Free Tier Limitations:
- **Sleep Mode**: Free apps sleep after 15 minutes of inactivity
- **Cold Start**: First request after sleep takes 30-60 seconds
- **Build Time**: 750 minutes/month limit
- **Bandwidth**: 100GB/month

### Performance Tips:
1. **Keep it alive**: Use a service like UptimeRobot to ping your app every 14 minutes
2. **Optimize requests**: Reduce unnecessary data extraction
3. **Monitor usage**: Check Render dashboard for resource usage

### Troubleshooting:

**If deployment fails:**
- Check the build logs in Render dashboard
- Ensure all dependencies are in `requirements.txt`
- Verify Python version compatibility

**If Playwright fails:**
- The build command includes `playwright install chromium`
- This installs the browser needed for Flipkart scraper

**If requests timeout:**
- Render has request timeout limits
- Consider reducing `max_results` parameter
- Add error handling for timeouts

## Cost Optimization

For production use, consider:
- **Paid Render plans** for better performance
- **Alternative platforms** like Railway, Heroku, or AWS
- **Caching strategies** to reduce API calls
- **Rate limiting** to prevent abuse

## Monitoring

Monitor your deployment:
- **Render Dashboard**: Check logs, metrics, and usage
- **API Health**: Test endpoints regularly
- **Performance**: Monitor response times
- **Errors**: Check logs for any issues
