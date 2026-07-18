# %%
import requests
import time
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
# Client names, page IDs, and ad account IDs have been replaced with placeholders.
clients = [
    {"name": "Client_01", "facebook_page_id": "PAGE_ID_01", "ad_account_id": "AD_ACCOUNT_01"},
    {"name": "Client_02", "facebook_page_id": "PAGE_ID_02", "ad_account_id": "AD_ACCOUNT_02"},
    {"name": "Client_03", "facebook_page_id": "PAGE_ID_03", "ad_account_id": "AD_ACCOUNT_03"},
    {"name": "Client_04", "facebook_page_id": "PAGE_ID_04", "ad_account_id": None},
    {"name": "Client_05", "facebook_page_id": "PAGE_ID_05", "ad_account_id": "AD_ACCOUNT_05"},
    {"name": "Client_06", "facebook_page_id": "PAGE_ID_06", "ad_account_id": "AD_ACCOUNT_06"},
    {"name": "Client_07", "facebook_page_id": "PAGE_ID_07", "ad_account_id": "AD_ACCOUNT_07"},
    {"name": "Client_08", "facebook_page_id": "PAGE_ID_08", "ad_account_id": "AD_ACCOUNT_08"},
    {"name": "Client_09", "facebook_page_id": "PAGE_ID_09", "ad_account_id": "AD_ACCOUNT_09"},
    {"name": "Client_10", "facebook_page_id": "PAGE_ID_10", "ad_account_id": "AD_ACCOUNT_10"},
]

# ================== CLIENTS TOKENS (Sanitized) ==================
# ⚠️ Note: All tokens have been replaced with placeholders.
clients_tokens = {
    "PAGE_ID_01": "TOKEN_01",
    "PAGE_ID_02": "TOKEN_02",
    "PAGE_ID_03": "TOKEN_03",
    "PAGE_ID_04": "TOKEN_04",
    "PAGE_ID_05": "TOKEN_05",
    "PAGE_ID_06": "TOKEN_06",
    "PAGE_ID_07": "TOKEN_07",
    "PAGE_ID_08": "TOKEN_08",
    "PAGE_ID_09": "TOKEN_09",
    "PAGE_ID_10": "TOKEN_10",
}

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

def get_campaigns_insights(ad_account_id, token, date_str):
    url = f"https://graph.facebook.com/v25.0/act_{ad_account_id}/insights"
    params = {
        "level": "campaign",
        "fields": "campaign_id,campaign_name,impressions,clicks,spend,cpc,cpm,ctr,actions,action_values,purchase_roas",
        "action_attribution_windows": ["1d_click", "7d_click", "28d_click", "1d_view", "7d_view"],
        "time_range": f'{{"since":"{date_str}","until":"{date_str}"}}',
        "access_token": token
    }
    return safe_get(url, params)

def extract_actions(actions_data):
    leads = 0
    purchases = 0
    if actions_data:
        for action in actions_data:
            action_type = action.get("action_type")
            value = int(action.get("value", 0))
            if action_type == "lead":
                leads = value
            elif action_type == "purchase":
                purchases = value
    return leads, purchases

def extract_revenue(action_values_data):
    revenue = 0.0
    if action_values_data:
        for action_value in action_values_data:
            action_type = action_value.get("action_type")
            value = float(action_value.get("value", 0))
            if action_type == "purchase":
                revenue += value
    return revenue

def extract_roas(purchase_roas_data):
    if purchase_roas_data and len(purchase_roas_data) > 0:
        return float(purchase_roas_data[0].get("value", 0))
    return 0.0

def save_campaigns_to_supabase(campaigns_data, client_facebook_page_id, client_name, target_date):
    for campaign in campaigns_data:
        actions = campaign.get("actions", [])
        leads, purchases = extract_actions(actions)
        
        action_values = campaign.get("action_values", [])
        revenue = extract_revenue(action_values)
        
        purchase_roas = campaign.get("purchase_roas", [])
        roas = extract_roas(purchase_roas)
        
        campaign_data = {
            "client_id": client_facebook_page_id,
            "client_name": client_name,
            "campaign_id": campaign.get("campaign_id"),
            "campaign_name": campaign.get("campaign_name"),
            "date": target_date,
            "spend": float(campaign.get("spend", 0)) if campaign.get("spend") else 0,
            "impressions": int(campaign.get("impressions", 0)) if campaign.get("impressions") else 0,
            "clicks": int(campaign.get("clicks", 0)) if campaign.get("clicks") else 0,
            "ctr": float(campaign.get("ctr", 0)) if campaign.get("ctr") else 0,
            "cpc": float(campaign.get("cpc", 0)) if campaign.get("cpc") else 0,
            "cpm": float(campaign.get("cpm", 0)) if campaign.get("cpm") else 0,
            "leads": leads,
            "purchases": purchases,
            "revenue": revenue,
            "roas": roas,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            result = supabase.table("campaigns_metrics").upsert(campaign_data).execute()
            print(f"   ✅ Saved: {campaign.get('campaign_name', campaign.get('campaign_id'))[:30]}...")
        except Exception as e:
            print(f"   ❌ Supabase Error: {str(e)}")
            print(f"   📝 Data: {str(campaign_data)[:200]}")

def run_yesterday_only():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"\n{'='*60}")
    print(f"🚀 RUNNING CAMPAIGNS METRICS ETL")
    print(f"📅 Date: {yesterday} (YESTERDAY)")
    print(f"👥 Total clients: {len(clients)}")
    print(f"{'='*60}")
    
    for client in clients:
        client_name = client["name"]
        facebook_page_id = client["facebook_page_id"]
        ad_account_id = client["ad_account_id"]
        token = clients_tokens.get(facebook_page_id)
        
        if not ad_account_id:
            print(f"\n⚠️ Client: {client_name} - No ad_account_id! Skipping.")
            continue
        
        if not token:
            print(f"\n⚠️ Client: {client_name} - No token found! Skipping.")
            continue
        
        print(f"\n👤 Client: {client_name}")
        print(f"   📢 Ad Account ID: act_{ad_account_id}")
        print(f"   📅 Date: {yesterday}")
        
        insights_data = get_campaigns_insights(ad_account_id, token, yesterday)
        
        if insights_data and "data" in insights_data:
            campaigns = insights_data["data"]
            print(f"   📊 Found {len(campaigns)} campaigns")
            save_campaigns_to_supabase(campaigns, facebook_page_id, client_name, yesterday)
        else:
            print(f"   ⚠️ No campaigns data found for {yesterday}")
            if insights_data:
                print(f"   📝 Response: {str(insights_data)[:200]}")
        
        time.sleep(0.5)
    
    print(f"\n{'='*60}")
    print("✅ ALL DONE!")
    print(f"{'='*60}")

if __name__ == "__main__":
    run_yesterday_only()
