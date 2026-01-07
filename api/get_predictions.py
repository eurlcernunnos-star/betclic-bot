from http.server import BaseHTTPRequestHandler
import json
import os
import psycopg2
from urllib.parse import urlparse

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        try:
            # Connect to Vercel Postgres
            # DATABASE_URL is automatically provided by Vercel when you link a database
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
            cur = conn.cursor()
            
            # Create Table if likely first run (Safety check)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id SERIAL PRIMARY KEY,
                    date TEXT,
                    league TEXT,
                    home TEXT,
                    away TEXT,
                    prediction TEXT,
                    odds REAL,
                    probability REAL,
                    edge REAL,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

            # Fetch valid predictions (Top 20 latest)
            cur.execute("SELECT id, date, league, home, away, prediction, odds, probability, edge, status FROM predictions ORDER BY created_at DESC LIMIT 20")
            rows = cur.fetchall()
            
            predictions = []
            for row in rows:
                predictions.append({
                    "id": row[0],
                    "date": row[1],
                    "league": row[2],
                    "home": row[3],
                    "away": row[4],
                    "prediction": row[5],
                    "odds": row[6],
                    "probability": row[7],
                    "edge": row[8],
                    "status": row[9]
                })

            self.wfile.write(json.dumps(predictions).encode('utf-8'))
            cur.close()
            conn.close()

        except Exception as e:
            error_msg = {"error": str(e), "message": "Database not connected or query failed."}
            self.wfile.write(json.dumps(error_msg).encode('utf-8'))
