import random
import json
import math
from datetime import datetime, timedelta

# --- Configuration ---
SIMULATION_COUNT = 100
MIN_EDGE_PERCENT = 5.0  # Only bet if we have > 5% edge
BANKROLL = 1000.0
STAKE_PERCENT = 2.0  # Flat staking

TEAMS = [
    "PSG", "Marseille", "Lyon", "Monaco", "Lille", "Lens", "Rennes", "Nice", 
    "Real Madrid", "Barcelona", "Atletico", "Sevilla", 
    "Man City", "Arsenal", "Liverpool", "Man Utd"
]

def poisson_probability(k, lamb):
    """Calculate Poisson probability of k events occurring with lambda rate."""
    return (lamb ** k * math.exp(-lamb)) / math.factorial(k)

def calculate_match_probabilities(home_xg, away_xg):
    """
    Calculate probabilities for Home Win, Draw, Away Win based on xG
    using Poisson distribution.
    """
    max_goals = 10
    home_probs = [poisson_probability(i, home_xg) for i in range(max_goals)]
    away_probs = [poisson_probability(i, away_xg) for i in range(max_goals)]

    prob_home_win = 0
    prob_draw = 0
    prob_away_win = 0

    for h in range(max_goals):
        for a in range(max_goals):
            p = home_probs[h] * away_probs[a]
            if h > a:
                prob_home_win += p
            elif h == a:
                prob_draw += p
            else:
                prob_away_win += p

    return prob_home_win, prob_draw, prob_away_win

def generate_realistic_match():
    """Simulate a match setup with teams and estimated strengths."""
    home_team = random.choice(TEAMS)
    away_team = random.choice([t for t in TEAMS if t != home_team])
    
    # Simulate team strengths (Goal Expectancy)
    # Stronger teams usually have higher xG
    home_strength = random.uniform(1.1, 2.5) 
    away_strength = random.uniform(0.8, 2.0)
    
    # Home advantage factor
    home_xg = home_strength * 1.1 
    away_xg = away_strength
    
    return home_team, away_team, home_xg, away_xg

def calculate_bookmaker_odds(prob_h, prob_d, prob_a):
    """
    Simulate bookmaker odds by adding a margin (vigorish).
    Standard bookie margin is around 5-7%.
    """
    margin = 0.05
    
    raw_odds_h = 1 / prob_h
    raw_odds_d = 1 / prob_d
    raw_odds_a = 1 / prob_a
    
    # Deflate odds to include margin
    odds_h = raw_odds_h / (1 + margin)
    odds_d = raw_odds_d / (1 + margin)
    odds_a = raw_odds_a / (1 + margin)
    
    return round(odds_h, 2), round(odds_d, 2), round(odds_a, 2)

def run_strategy():
    print(f"--- Starting Strategy Simulation (Poisson Model) ---")
    print(f"Bankroll: ${BANKROLL}")
    print(f"Min Edge Required: {MIN_EDGE_PERCENT}%")
    
    current_bankroll = BANKROLL
    match_history = []
    predictions = []
    
    wins = 0
    losses = 0
    total_staked = 0
    
    # Generate dates for next few days
    today = datetime.now()
    
    print("\n--- Analyzing Matches ---")
    
    for i in range(SIMULATION_COUNT):
        home, away, h_xg, a_xg = generate_realistic_match()
        
        # 1. Our Model's Probabilities
        my_prob_h, my_prob_d, my_prob_a = calculate_match_probabilities(h_xg, a_xg)
        
        # 2. Convert to 'Fair Odds' (What odds SHOULD be)
        my_odds_h = 1 / my_prob_h if my_prob_h > 0 else 0
        
        # 3. Simulate Bookmaker Odds (Adding some random noise/inefficiency to create value opportunities)
        # We slightly distort the bookie probs to simulate 'bad pricing'
        bookie_prob_h = my_prob_h * random.uniform(0.85, 1.15) 
        bookie_prob_d = my_prob_d * random.uniform(0.85, 1.15)
        bookie_prob_a = my_prob_a * random.uniform(0.85, 1.15)
        
        # Normalize
        total = bookie_prob_h + bookie_prob_d + bookie_prob_a
        bookie_prob_h /= total
        bookie_prob_d /= total
        bookie_prob_a /= total
        
        odds_h, odds_d, odds_a = calculate_bookmaker_odds(bookie_prob_h, bookie_prob_d, bookie_prob_a)
        
        # 4. Find Value
        # Edge = (Probability * Odds) - 1
        edge_h = (my_prob_h * odds_h) - 1
        
        prediction_data = {
            "id": i + 1,
            "date": (today + timedelta(days=random.randint(0, 3))).strftime("%Y-%m-%d %H:%M"),
            "league": "Ligue 1" if home in ["PSG", "Marseille", "Lens"] else "Champions League",
            "home": home,
            "away": away,
            "prediction": "HOME WIN",
            "odds": odds_h,
            "probability": round(my_prob_h * 100, 1),
            "edge": round(edge_h * 100, 1),
            "status": "PENDING"
        }
        
        # Simulating the Result using the True xG
        # Poisson Simulation of actual goals
        actual_goals_h = 0
        actual_goals_a = 0
        p = 1.0
        for k in range(10):
            p *= random.random()
            if p < math.exp(-h_xg):
                actual_goals_h = k
                break
        p = 1.0
        for k in range(10):
            p *= random.random()
            if p < math.exp(-a_xg):
                actual_goals_a = k
                break
                
        # Bet Placement
        if edge_h * 100 > MIN_EDGE_PERCENT:
            stake = BANKROLL * (STAKE_PERCENT / 100)
            total_staked += stake
            
            # Determine outcome
            is_win = actual_goals_h > actual_goals_a
            
            if is_win:
                profit = stake * (odds_h - 1)
                current_bankroll += profit
                wins += 1
                prediction_data["result"] = "WON"
                print(f"[BET HEADLINE] {home} vs {away} | Odds: {odds_h} | Edge: {prediction_data['edge']}% | Result: {actual_goals_h}-{actual_goals_a} (WIN)")
            else:
                current_bankroll -= stake
                losses += 1
                prediction_data["result"] = "LOST"
                print(f"[bet]          {home} vs {away} | Odds: {odds_h} | Edge: {prediction_data['edge']}% | Result: {actual_goals_h}-{actual_goals_a} (LOSS)")
                
            predictions.append(prediction_data)

    # Stats
    total_bets = wins + losses
    if total_bets > 0:
        win_rate = (wins / total_bets) * 100
        roi = ((current_bankroll - BANKROLL) / total_staked) * 100
    else:
        win_rate = 0
        roi = 0

    print("\n--- Simulation Results ---")
    print(f"Total Bets Found: {total_bets}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Final Bankroll: ${current_bankroll:.2f}")
    print(f"ROI: {roi:.2f}%")
    
    # Save to JSON for Frontend
    # Sort by Edge (Highest First) and take top 12
    predictions.sort(key=lambda x: x["edge"], reverse=True)
    top_predictions = predictions[:12]
    
    output_file = "Web/predictions.json"
    # Ensure Web dir exists (python won't create it automatically if we don't manage it, but good practice to just save in root for now then move or just ensure path)
    # NOTE: The user asked for "Web" folder structure in next phase, so I will save it to the current dir for now or create the folder.
    # Actually, I'll save to 'predictions.json' in root and 'Web/predictions.json' if directory exists.
    
    with open("predictions.json", "w") as f:
        json.dump(top_predictions, f, indent=4)
        
    print(f"Saved {len(top_predictions)} high-value predictions to predictions.json")

if __name__ == "__main__":
    run_strategy()
