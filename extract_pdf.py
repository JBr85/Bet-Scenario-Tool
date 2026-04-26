# Script to extract data from PDF and add to database
import pdfplumber
import sqlite3
import re
from datetime import datetime

DATABASE = 'bets.db'

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        match TEXT,
        bet_type TEXT,
        market TEXT,
        stake REAL,
        matched REAL,
        status TEXT,
        pnl REAL,
        country TEXT,
        league TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    conn.commit()
    conn.close()
    print("Database initialized")

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Team to country/league mapping
TEAM_MAP = {
    'liverpool': ('England', 'Premier League'),
    'manchester': ('England', 'Premier League'),
    'chelsea': ('England', 'Premier League'),
    'arsenal': ('England', 'Premier League'),
    'tottenham': ('England', 'Premier League'),
    'newcastle': ('England', 'Premier League'),
    'aston villa': ('England', 'Premier League'),
    'city': ('England', 'Premier League'),
    'united': ('England', 'Premier League'),
    'brentford': ('England', 'Premier League'),
    'nottingham': ('England', 'Premier League'),
    'crystal palace': ('England', 'Premier League'),
    'fulham': ('England', 'Premier League'),
    'brighton': ('England', 'Premier League'),
    'bournemouth': ('England', 'Premier League'),
    'barcelona': ('Spain', 'La Liga'),
    'real madrid': ('Spain', 'La Liga'),
    'madrid': ('Spain', 'La Liga'),
    'atletico': ('Spain', 'La Liga'),
    'villarreal': ('Spain', 'La Liga'),
    'sevilla': ('Spain', 'La Liga'),
    'athletic': ('Spain', 'La Liga'),
    'betis': ('Spain', 'La Liga'),
    'elche': ('Spain', 'La Liga'),
    'osasuna': ('Spain', 'La Liga'),
    'oviedo': ('Spain', 'La Liga'),
    'mallorca': ('Spain', 'La Liga'),
    'juventus': ('Italy', 'Serie A'),
    'milan': ('Italy', 'Serie A'),
    'inter': ('Italy', 'Serie A'),
    'roma': ('Italy', 'Serie A'),
    'napoli': ('Italy', 'Serie A'),
    'lecce': ('Italy', 'Serie A'),
    'bayern': ('Germany', 'Bundesliga'),
    'dortmund': ('Germany', 'Bundesliga'),
    'borussia': ('Germany', 'Bundesliga'),
    'leipzig': ('Germany', 'Bundesliga'),
    'leverkusen': ('Germany', 'Bundesliga'),
    'stuttgart': ('Germany', 'Bundesliga'),
    'mainz': ('Germany', 'Bundesliga'),
    'wolfsburg': ('Germany', 'Bundesliga'),
    'heidenheim': ('Germany', 'Bundesliga'),
    'union berlin': ('Germany', 'Bundesliga'),
    'psg': ('France', 'Ligue 1'),
    'paris': ('France', 'Ligue 1'),
    'monaco': ('France', 'Ligue 1'),
    'rennes': ('France', 'Ligue 1'),
    'lorient': ('France', 'Ligue 1'),
    'le havre': ('France', 'Ligue 1'),
    'atlanta': ('USA', 'MLS'),
    'cincinnati': ('USA', 'MLS'),
    'genk': ('Belgium', 'Pro League'),
    'porto': ('Portugal', 'Primeira Liga'),
    'sporting': ('Portugal', 'Primeira Liga'),
    'guimaraes': ('Portugal', 'Primeira Liga'),
    'estoril': ('Portugal', 'Primeira Liga'),
    'fenerbahçe': ('Turkey', 'Super Lig'),
    'beşiktaş': ('Turkey', 'Super Lig'),
    'kayserispor': ('Turkey', 'Super Lig'),
    'rizespor': ('Turkey', 'Super Lig'),
    'konyaspor': ('Turkey', 'Super Lig'),
    'göztepe': ('Turkey', 'Super Lig'),
    'eyüpspor': ('Turkey', 'Super Lig'),
    'utrecht': ('Netherlands', 'Eredivisie'),
    'az': ('Netherlands', 'Eredivisie'),
    'alkmaar': ('Netherlands', 'Eredivisie'),
    'twente': ('Netherlands', 'Eredivisie'),
    'excelsior': ('Netherlands', 'Eredivisie'),
    'telstar': ('Netherlands', 'Eredivisie'),
    'heerenveen': ('Netherlands', 'Eredivisie'),
    'groningen': ('Netherlands', 'Eredivisie'),
    'rangers': ('Scotland', 'Scottish Premiership'),
    'charlton': ('England', 'Championship'),
    'derby': ('England', 'Championship'),
    'birmingham': ('England', 'Championship'),
    'stoke': ('England', 'Championship'),
    'bristol city': ('England', 'Championship'),
    'sheffield': ('England', 'Championship'),
    'ipswich': ('England', 'Championship'),
    'millwall': ('England', 'Championship'),
    'swansea': ('England', 'Championship'),
    'southampton': ('England', 'Championship'),
    'portsmouth': ('England', 'Championship'),
    'oh leuven': ('Belgium', 'Pro League'),
    'union st. gilloise': ('Belgium', 'Pro League'),
    'antwerp': ('Belgium', 'Pro League'),
    'st. truyen': ('Belgium', 'Pro League'),
    'dender': ('Belgium', 'Pro League'),
    'paok': ('Greece', 'Super League'),
    'real betis': ('Spain', 'La Liga'),
}

LEAGUE_MAP = {
    'Premier League': ('England', 'Premier League'),
    'La Liga': ('Spain', 'La Liga'),
    'Bundesliga': ('Germany', 'Bundesliga'),
    'Serie A': ('Italy', 'Serie A'),
    'Ligue 1': ('France', 'Ligue 1'),
    'Championship': ('England', 'Championship'),
    'MLS': ('USA', 'MLS'),
    'Super Lig': ('Turkey', 'Super Lig'),
    'Eredivisie': ('Netherlands', 'Eredivisie'),
    'Primeira Liga': ('Portugal', 'Primeira Liga'),
    'Jupiler Pro League': ('Belgium', 'Pro League'),
    'UEFA Champions League': ('Europe', 'Champions League'),
    'UEFA Europa League': ('Europe', 'Europa League'),
    'Süper Lig': ('Turkey', 'Super Lig'),
    'Scottish Premiership': ('Scotland', 'Scottish Premiership'),
    'Super League': ('Greece', 'Super League'),
}

def extract_country_league(match, league_text):
    # First try league text
    for league, (country, league_name) in LEAGUE_MAP.items():
        if league.lower() in league_text.lower():
            return country, league_name
    
    # Then try team mapping
    match_lower = match.lower()
    for team, (country, league) in TEAM_MAP.items():
        if team in match_lower:
            return country, league
    
    return 'Unknown', 'Other'

def parse_pdf():
    pdf_path = 'BetsoccerPro Results April.pdf'
    bets = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            for line in lines:
                # Match pattern: "Team vs Team Back Over X.X Goals ... WIN/LOSS"
                # Example: "Newcastle vs Aston Villa Back Over 1.5 Goals 63' minute At rec: 0-1 WIN"
                
                # Skip lines that don't have the pattern
                if ' vs ' not in line:
                    continue
                if 'Back Over' not in line and 'Over' not in line:
                    continue
                if 'WIN' not in line and 'LOSS' not in line:
                    continue
                
                # Extract match
                parts = line.split(' vs ')
                if len(parts) < 2:
                    continue
                
                team1 = parts[0].strip()
                rest = ' vs '.join(parts[1:])
                
                # Find team2 and bet type
                bet_type_match = re.search(r'(Back Over|Over) [\d.]+ Goals', rest)
                if not bet_type_match:
                    continue
                
                bet_type = bet_type_match.group(0)
                
                # Find the second team (everything before bet type)
                rest_before_bet = rest[:bet_type_match.start()].strip()
                team2_parts = rest_before_bet.rsplit(' ', 1)
                team2 = team2_parts[-1].strip() if team2_parts else rest_before_bet
                
                match_name = f"{team1} vs {team2}"
                
                # Extract result
                is_win = 'WIN' in line
                is_loss = 'LOSS' in line
                
                # Extract league
                league = 'Unknown'
                for lg in LEAGUE_MAP.keys():
                    if lg in line:
                        league = lg
                        break
                
                # Extract date
                date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d+, \d{4}', line)
                if date_match:
                    date_str = date_match.group(0)
                    try:
                        date_obj = datetime.strptime(date_str, '%b %d, %Y')
                        date = date_obj.strftime('%Y-%m-%d')
                    except:
                        date = date_str
                else:
                    date = '2026-01-01'
                
                # Extract country and league
                country, league_name = extract_country_league(match_name, line)
                
                # Calculate P&L (placeholder - would need stake data)
                # For now, use a default stake
                stake = 30.0
                pnl = 20.0 if is_win else -30.0
                
                bets.append({
                    'date': date,
                    'match': match_name,
                    'bet_type': bet_type,
                    'market': 'Live',
                    'stake': stake,
                    'matched': stake,
                    'status': 'Settled',
                    'pnl': pnl,
                    'country': country,
                    'league': league_name
                })
    
    return bets

def add_bets_to_db(bets):
    conn = get_db()
    c = conn.cursor()
    added = 0
    duplicates = 0
    
    for bet in bets:
        # Check for duplicates based on date, match, and pnl
        c.execute('SELECT id FROM bets WHERE date = ? AND match = ? AND pnl = ?',
                  (bet['date'], bet['match'], bet['pnl']))
        if c.fetchone():
            duplicates += 1
            continue
            
        c.execute('''INSERT INTO bets 
            (date, match, bet_type, market, stake, matched, status, pnl, country, league)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (bet['date'], bet['match'], bet['bet_type'], bet['market'],
             bet['stake'], bet['matched'], bet['status'], bet['pnl'],
             bet['country'], bet['league']))
        added += 1
    
    conn.commit()
    conn.close()
    print(f"Added {added} new bets from PDF, {duplicates} duplicates skipped")
    return added

if __name__ == '__main__':
    init_db()
    bets = parse_pdf()
    print(f"Extracted {len(bets)} bets from PDF")
    if bets:
        add_bets_to_db(bets)