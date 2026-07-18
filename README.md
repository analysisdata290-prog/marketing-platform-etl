# marketing-platform-etl
ETL pipeline for marketing analytics platform (portfolio version)
# Marketing Platform ETL Pipeline

## Overview
This project automates data collection from multiple ad platforms (Meta, Google, GA4, Snapchat) and loads it into Supabase PostgreSQL for the Marketing Analytics Platform.

## Architecture


## Data Sources
- **Meta Ads API** → Campaign performance data
- **Google Ads API** → Campaign performance data
- **GA4 API** → Website analytics data
- **Snapchat Ads API** → Campaign performance data

## Schedule
- **Platform:** GitHub Actions
- **Frequency:** Daily at 6:00 AM
- **Data Freshness:** Last 24 hours

## Technologies
- Python 3.9+
- pandas, requests, psycopg2-binary
- Supabase PostgreSQL
- GitHub Actions

## Setup (for recruiters)
1. Clone the repository
2. Create a `.env` file (see `.env.example`)
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `python src/campaigns_etl.py`

## Note
This is a **sanitized version** for portfolio purposes. All sensitive data (API keys, passwords, client names) has been removed.
-
- [رابط GitHub بتاعك]
