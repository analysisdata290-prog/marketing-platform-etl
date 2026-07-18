# %%
import requests
import os
from datetime import date, timedelta
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ================== SUPABASE CONFIG ==================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================== CLIENTS DATA (Sanitized) ==================
# ⚠️ Note: This is a sanitized version for portfolio purposes.
# Client names, page IDs, and tokens have been replaced with placeholders.
clients = [
    {"name": "Client_01", "page_id": "PAGE_ID_01", "token": "TOKEN_01"},
    {"name": "Client_02", "page_id": "PAGE_ID_02", "token": "TOKEN_02"},
    {"name": "Client_03", "page_id": "PAGE_ID_03", "token": "TOKEN_03"},
    {"name": "Client_04", "page_id": "PAGE_ID_04", "token": "TOKEN_04"},
    {"name": "Client_05", "page_id": "PAGE_ID_05", "token": "TOKEN_05"},
    {"name": "Client_06", "page_id": "PAGE_ID_06", "token": "TOKEN_06"},
]

def safe_get(url, params):
    try:
        res = requests.get(url, params=params, timeout=30)
        data = res.json()
        if "error" in data:
            print("❌ FB ERROR:", data["error"])
            return None
        return data
    except Exception as e:
        print(f"❌ Request Error: {str(e)[:100]}")
        return None

def get_facebook_insights(page_id, token):
    url = f"https://graph.facebook.com/v18.0/{page_id}/insights"
    params = {
        "metric": "page_impressions_unique,page_post_engagements,page_daily_follows",
        "period": "day",
        "access_token": token
    }
    return safe_get(url, params)

def parse_fb(data):
    metrics = {"impressions": 0, "engagement": 0, "profile_visits": 0, "reach": 0}
    if not data or "data" not in data:
        return metrics
    for item in data.get("data", []):
        name = item.get("name")
        values = item.get("values", [])
        if values:
            value = values[0].get("value", 0)
            if name == "page_impressions_unique":
                metrics["impressions"] = value
                metrics["reach"] = value
            elif name == "page_post_engagements":
                metrics["engagement"] = value
            elif name == "page_daily_follows":
                metrics["profile_visits"] = value
    return metrics

def get_facebook_followers(page_id, token):
    url = f"https://graph.facebook.com/v18.0/{page_id}"
    params = {
        "fields": "followers_count",
        "access_token": token
    }
    data = safe_get(url, params)
    if data:
        return data.get("followers_count", 0)
    return 0

def get_instagram_id(page_id, token):
    url = f"https://graph.facebook.com/v18.0/{page_id}"
    params = {
        "fields": "instagram_business_account",
        "access_token": token
    }
    data = safe_get(url, params)
    if not data:
        return None
    return data.get("instagram_business_account", {}).get("id")

def get_instagram_followers(ig_id, token):
    url = f"https://graph.facebook.com/v18.0/{ig_id}"
    params = {
        "fields": "followers_count",
        "access_token": token
    }
    data = safe_get(url, params)
    if data:
        return data.get("followers_count", 0)
    return 0

def get_instagram_posts_insights_workaround(ig_id, token, target_date):
    total_views = 0
    total_likes = 0
    total_comments = 0
    total_shares = 0
    total_saved = 0
    
    url = f"https://graph.facebook.com/v18.0/{ig_id}/media"
    params = {
        "fields": "id",
        "since": f"{target_date}T00:00:00+0000",
        "until": f"{target_date}T23:59:59+0000",
        "limit": 50,
        "access_token": token
    }
    
    media_response = safe_get(url, params)
    
    if not media_response or "data" not in media_response:
        return {"impressions": 0, "engagement": 0, "profile_views": 0, "reach": 0}
    
    for post in media_response.get("data", []):
        post_id = post["id"]
        
        insights_url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
        insights_params = {
            "metric": "views,likes,comments,shares,saved",
            "access_token": token
        }
        
        insights = safe_get(insights_url, insights_params)
        
        if insights and "data" in insights:
            for metric in insights.get("data", []):
                name = metric.get("name")
                values = metric.get("values", [])
                if values:
                    value = values[0].get("value", 0)
                    if name == "views":
                        total_views += value
                    elif name == "likes":
                        total_likes += value
                    elif name == "comments":
                        total_comments += value
                    elif name == "shares":
                        total_shares += value
                    elif name == "saved":
                        total_saved += value
    
    profile_views = 0
    profile_url = f"https://graph.facebook.com/v18.0/{ig_id}/insights"
    profile_params = {
        "metric": "profile_views",
        "period": "day",
        "metric_type": "total_value",
        "access_token": token
    }
    profile_response = safe_get(profile_url, profile_params)
    if profile_response and "data" in profile_response:
        for item in profile_response.get("data", []):
            if item.get("name") == "profile_views":
                values = item.get("values", [])
                if values:
                    profile_views = values[0].get("value", 0)
    
    total_engagement = total_likes + total_comments + total_shares + total_saved
    
    return {
        "impressions": total_views,
        "engagement": total_engagement,
        "profile_views": profile_views,
        "reach": total_views
    }

def run():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    
    for c in clients:
        print(f"\nProcessing {c['name']} for {yesterday}...")
        
        # Facebook Data
        fb_raw = get_facebook_insights(c["page_id"], c["token"])
        fb = parse_fb(fb_raw)
        fb_followers = get_facebook_followers(c["page_id"], c["token"])
        
        print(f"   ✅ Facebook: impressions={fb['impressions']}, engagement={fb['engagement']}, profile_visits={fb['profile_visits']}, reach={fb['reach']}, followers={fb_followers}")
        
        supabase.table("daily_account_metrics").upsert({
            "client_id": c["page_id"],
            "client_name": c["name"],
            "date": yesterday,
            "platform": "facebook",
            "followers": fb_followers,
            "impressions": fb["impressions"],
            "reach": fb["reach"],
            "profile_visits": fb["profile_visits"],
            "engagement": fb["engagement"],
            "video_views": 0
        }).execute()
        
        # Instagram Data
        ig_id = get_instagram_id(c["page_id"], c["token"])
        
        if ig_id:
            print(f"   Instagram ID: {ig_id}")
            ig_followers = get_instagram_followers(ig_id, c["token"])
            ig_data = get_instagram_posts_insights_workaround(ig_id, c["token"], yesterday)
            print(f"   ✅ Instagram: impressions={ig_data['impressions']}, engagement={ig_data['engagement']}, profile_views={ig_data['profile_views']}, reach={ig_data['reach']}, followers={ig_followers}")
            
            supabase.table("daily_account_metrics").upsert({
                "client_id": c["page_id"],
                "client_name": c["name"],
                "date": yesterday,
                "platform": "instagram",
                "followers": ig_followers,
                "impressions": ig_data["impressions"],
                "reach": ig_data["reach"],
                "profile_visits": ig_data["profile_views"],
                "engagement": ig_data["engagement"],
                "video_views": 0
            }).execute()
        else:
            print(f"   ❌ Instagram: No business account linked")
            supabase.table("daily_account_metrics").upsert({
                "client_id": c["page_id"],
                "client_name": c["name"],
                "date": yesterday,
                "platform": "instagram",
                "followers": 0,
                "impressions": 0,
                "reach": 0,
                "profile_visits": 0,
                "engagement": 0,
                "video_views": 0
            }).execute()
    
    print("\n✅ DONE ✔")

if __name__ == "__main__":
    run()
