from http.server import BaseHTTPRequestHandler
import json
import os
import psycopg2
import random
import math
from datetime import datetime, timedelta

# --- Strategy Logic Same as before ---
TEAMS = [
    "PSG", "Marseille", "Lyon", "Monaco", "Lille", "Lens", "Rennes", "Nice", 
    "Real Madrid", "Barcelona", "Atletico", "Sevilla", 
    "Man City", "Arsenal", "Liverpool", "Man Utd"
]

def poisson_probability(k, lamb):
    return (lamb ** k * math.exp(-lamb)) / math.factorial(k)

def calculate_match_probabilities(home_xg, away_xg):
    max_goals = 10
    home_probs = [poisson_probability(i, home_xg) for i in range(max_goals)]
    away_probs = [poisson_probability(i, away_xg) for i in range(max_goals)]
    prob_home_win = 0
    prob_draw = 0
    prob_away_win = 0
    for h in range(max_goals):
        for a in range(max_goals):
            p = home_probs[h] * away_probs[a]
            if h > a: prob_home_win += p
            elif h == a: prob_draw += p
            else: prob_away_win += p
    return prob_home_win, prob_draw, prob_away_win

def calculate_bookmaker_odds(prob_h, prob_d, prob_a):
    margin = 0.05
    odds_h = (1 / prob_h) / (1 + margin)
    odds_d = (1 / prob_d) / (1 + margin)
    odds_a = (1 / prob_a) / (1 + margin)
    return round(odds_h, 2), round(odds_d, 2), round(odds_a, 2)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Vercel Cron Authentication Check
        # Vercel sends `Authorization: Bearer <token>` header for cron jobs usually
        # For simplicity here we just run it.
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        new_predictions = []
        today = datetime.now()

        # Run 100 Simulations to find EDGE
        for i in range(100):
            home_team = random.choice(TEAMS)
            away_team = random.choice([t for t in TEAMS if t != home_team])
            home_strength = random.uniform(1.1, 2.5) 
            away_strength = random.uniform(0.8, 2.0)
            home_xg = home_strength * 1.1 
            away_xg = away_strength

            my_prob_h, my_prob_d, my_prob_a = calculate_match_probabilities(home_xg, away_xg)
            
            # Simulate Bookie
            bookie_prob_h = my_prob_h * random.uniform(0.85, 1.15) 
            bookie_prob_d = my_prob_d * random.uniform(0.85, 1.15)
            bookie_prob_a = my_prob_a * random.uniform(0.85, 1.15)
            
            # Normalize
            total = bookie_prob_h + bookie_prob_d + bookie_prob_a
            bookie_prob_h /= total
            bookie_prob_d /= total
            bookie_prob_a /= total

            odds_h, odds_d, odds_a = calculate_bookmaker_odds(bookie_prob_h, bookie_prob_d, bookie_prob_a)
            
            # Calculate Edge
            edge_h = (my_prob_h * odds_h) - 1
            
            if edge_h * 100 > 5.0: # 5% Edge
                new_predictions.append({
                    "date": (today + timedelta(days=random.randint(0, 3))).strftime("%Y-%m-%d %H:%M"),
                    "league": "Ligue 1" if home_team in ["PSG", "Marseille"] else "Champions League",
                    "home": home_team,
                    "away": away_team,
                    "prediction": "HOME WIN",
                    "odds": odds_h,
                    "probability": round(my_prob_h * 100, 1),
                    "edge": round(edge_h * 100, 1),
                    "status": "PENDING"
                })

        # Save to Database
        try:
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
            cur = conn.cursor()
            
            # Ensure table exists
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
            
            # Clear old "Pending" to keep it fresh (optional, or just append)
            # cur.execute("DELETE FROM predictions WHERE status = 'PENDING'") 
            
            count = 0
            for p in new_predictions[:10]: # Save top 10
                cur.execute(
                    "INSERT INTO predictions (date, league, home, away, prediction, odds, probability, edge, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (p['date'], p['league'], p['home'], p['away'], p['prediction'], p['odds'], p['probability'], p['edge'], p['status'])
                )
                count += 1
            
            conn.commit()
            cur.close()
            conn.close()
            
            msg = {"status": "success", "added": count}
        except Exception as e:
            msg = {"status": "error", "details": str(e)}

        self.wfile.write(json.dumps(msg).encode('utf-8'))
