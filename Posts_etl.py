import requests
import re
import time
import sys
import os
from datetime import datetime, timedelta
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

def safe_get(url, params, max_retries=3):
    for attempt in range(max_retries):
        try:
            res = requests.get(url, params=params, timeout=30)
            data = res.json()
            if "error" in data:
                print(f"   ⚠️ API Error (attempt {attempt+1}): {data['error'].get('message', 'Unknown')[:100]}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
            return data
        except Exception as e:
            print(f"   ⚠️ Request Error (attempt {attempt+1}): {str(e)[:100]}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
    return None

def extract_hashtags(text):
    if not text:
        return []
    return re.findall(r'#(\w+)', text)

def extract_mentions(text):
    if not text:
        return []
    return re.findall(r'@(\w+)', text)

def get_instagram_id(page_id, token):
    url = f"https://graph.facebook.com/v18.0/{page_id}"
    params = {"fields": "instagram_business_account", "access_token": token}
    data = safe_get(url, params)
    if not data:
        return None
    return data.get("instagram_business_account", {}).get("id")

def get_instagram_posts_insights(ig_id, token, since_date, until_date, client_name, client_page_id):
    posts_data = []
    url = f"https://graph.facebook.com/v18.0/{ig_id}/media"
    params = {
        "fields": "id,caption,media_type,media_url,permalink,timestamp",
        "since": since_date,
        "until": until_date,
        "limit": 50,
        "access_token": token
    }
    media_response = safe_get(url, params)
    if not media_response or "data" not in media_response:
        return posts_data
    
    for post in media_response["data"]:
        post_id = post["id"]
        media_type = post.get("media_type", "UNKNOWN")
        
        if media_type == "VIDEO":
            metrics_to_request = "reach,likes,comments,shares,saved,views"
        else:
            metrics_to_request = "reach,likes,comments,shares,saved"
        
        insights_url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
        insights_params = {
            "metric": metrics_to_request,
            "access_token": token
        }
        insights = safe_get(insights_url, insights_params)
        metrics = {"reach": 0, "likes": 0, "comments": 0, "shares": 0, "saved": 0, "views": 0}
        
        if insights and "data" in insights:
            for item in insights["data"]:
                name = item["name"]
                values = item.get("values", [])
                if values:
                    metrics[name] = values[0].get("value", 0)
        
        total_engagement = metrics["likes"] + metrics["comments"] + metrics["shares"] + metrics["saved"]
        caption_text = post.get("caption", "")
        hashtags = extract_hashtags(caption_text)
        mentions = extract_mentions(caption_text)
        
        if media_type == "VIDEO":
            post_type = "reel"
        elif media_type == "CAROUSEL_ALBUM":
            post_type = "carousel"
        else:
            post_type = "post"
        
        posts_data.append({
            "client_id": client_page_id,
            "client_name": client_name,
            "post_id": post_id,
            "caption": caption_text[:500],
            "media_type": media_type,
            "media_url": post.get("media_url", ""),
            "permalink": post.get("permalink", ""),
            "posted_at": post.get("timestamp"),
            "reach": metrics["reach"],
            "impressions": metrics["views"] if media_type == "VIDEO" else metrics["reach"],
            "likes": metrics["likes"],
            "comments": metrics["comments"],
            "shares": metrics["shares"],
            "saves": metrics["saved"],
            "engagement": total_engagement,
            "video_views": metrics["views"] if media_type == "VIDEO" else 0,
            "platform": "instagram",
            "post_type": post_type,
            "hashtags": hashtags,
            "mentions": mentions,
            "created_at": datetime.now().isoformat()
        })
        time.sleep(0.3)
    return posts_data

def get_facebook_posts_insights(page_id, token, since_date, until_date, client_name):
    posts_data = []
    url = f"https://graph.facebook.com/v18.0/{page_id}/posts"
    params = {
        "fields": "id,message,created_time,attachments{media_type,media_url,target{url}},permalink_url",
        "since": since_date,
        "until": until_date,
        "limit": 50,
        "access_token": token
    }
    posts_response = safe_get(url, params)
    if not posts_response or "data" not in posts_response:
        return posts_data
    
    for post in posts_response["data"]:
        post_id = post["id"]
        
        insights_url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
        insights_params = {
            "metric": "post_reactions_like_total,post_comments,post_shares,post_saves,post_impressions_unique",
            "access_token": token
        }
        insights = safe_get(insights_url, insights_params)
        metrics = {
            "post_reactions_like_total": 0,
            "post_comments": 0,
            "post_shares": 0,
            "post_saves": 0,
            "post_impressions_unique": 0
        }
        
        if insights and "data" in insights:
            for item in insights["data"]:
                name = item["name"]
                values = item.get("values", [])
                if values:
                    metrics[name] = values[0].get("value", 0)
        
        total_engagement = metrics["post_reactions_like_total"] + metrics["post_comments"] + metrics["post_shares"] + metrics["post_saves"]
        message_text = post.get("message", "")
        hashtags = extract_hashtags(message_text)
        mentions = extract_mentions(message_text)
        
        attachments = post.get("attachments", {}).get("data", [])
        media_type = "TEXT"
        post_type = "post"
        media_url = ""
        
        if attachments:
            attachment = attachments[0]
            media_type = attachment.get("media_type", "UNKNOWN")
            if media_type == "video":
                post_type = "video"
                media_url = attachment.get("media_url", "")
            elif media_type in ["photo", "image"]:
                post_type = "photo"
                media_url = attachment.get("media_url", "")
            elif "target" in attachment and "url" in attachment["target"]:
                media_url = attachment["target"]["url"]
        
        posts_data.append({
            "client_id": page_id,
            "client_name": client_name,
            "post_id": post_id,
            "caption": message_text[:500],
            "media_type": media_type,
            "media_url": media_url,
            "permalink": post.get("permalink_url", ""),
            "posted_at": post.get("created_time"),
            "reach": metrics["post_impressions_unique"],
            "impressions": metrics["post_impressions_unique"],
            "likes": metrics["post_reactions_like_total"],
            "comments": metrics["post_comments"],
            "shares": metrics["post_shares"],
            "saves": metrics["post_saves"],
            "engagement": total_engagement,
            "video_views": metrics["post_impressions_unique"] if media_type == "video" else 0,
            "platform": "facebook",
            "post_type": post_type,
            "hashtags": hashtags,
            "mentions": mentions,
            "created_at": datetime.now().isoformat()
        })
        time.sleep(0.3)
    return posts_data

def save_posts_to_supabase(posts_data):
    if not posts_data:
        return
    for post in posts_data:
        try:
            supabase.table("posts_metrics").upsert(post).execute()
            print(f"   ✅ Saved/Updated: {post['post_id'][:15]}... ({post['platform']})")
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Error saving {post['post_id'][:15]}...: {error_msg[:100]}")

def run_yesterday_only():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    since = f"{yesterday}T00:00:00+0000"
    until = f"{yesterday}T23:59:59+0000"
    
    print(f"\n{'='*60}")
    print(f"🚀 RUNNING POSTS METRICS ETL")
    print(f"📅 Date: {yesterday} (YESTERDAY)")
    print(f"👥 Total clients: {len(clients)}")
    print(f"{'='*60}")
    
    for client in clients:
        print(f"\n👤 Client: {client['name']}")
        
        fb_posts = get_facebook_posts_insights(client["page_id"], client["token"], since, until, client["name"])
        print(f"   📘 Facebook: {len(fb_posts)} posts found")
        save_posts_to_supabase(fb_posts)
        
        ig_id = get_instagram_id(client["page_id"], client["token"])
        if ig_id:
            insta_posts = get_instagram_posts_insights(ig_id, client["token"], since, until, client["name"], client["page_id"])
            print(f"   📸 Instagram: {len(insta_posts)} posts found")
            save_posts_to_supabase(insta_posts)
        else:
            print(f"   📸 Instagram: No business account linked")
        
        time.sleep(0.5)
    
    print(f"\n{'='*60}")
    print("✅ ALL DONE!")
    print(f"{'='*60}")

if __name__ == "__main__":
    run_yesterday_only()
