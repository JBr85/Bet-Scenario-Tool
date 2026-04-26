from flask import Flask, render_template, request, jsonify
import pandas as pd
import sqlite3
import os
import re
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bet-scenario-tool-secret-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DATABASE = 'bets.db'

data_store = {
    'data': [],
    'leagues': [],
    'markets': [],
    'results': None,
    'config': {
        'selected_leagues': [],
        'selected_markets': [],
        'odds_min': 1.0,
        'odds_max': 100.0,
        'staking_strategy': 'flat',
        'daily_bank': 1000,
        'stake_percentage': 2,
        'base_stake': 20,
        'timeframe': 'all',
        'date_start': None,
        'date_end': None,
        'time_start': None,
        'time_end': None,
        'commission': 2.0,
    }
}

# ==================== TEAM/LEAGUE INTELLIGENCE ====================

TEAM_MAP = {
    'liverpool': ('England', 'Premier League'),
    'manchester city': ('England', 'Premier League'),
    'manchester united': ('England', 'Premier League'),
    'man city': ('England', 'Premier League'),
    'man utd': ('England', 'Premier League'),
    'chelsea': ('England', 'Premier League'),
    'arsenal': ('England', 'Premier League'),
    'tottenham': ('England', 'Premier League'),
    'newcastle': ('England', 'Premier League'),
    'aston villa': ('England', 'Premier League'),
    'brentford': ('England', 'Premier League'),
    'nottingham forest': ('England', 'Premier League'),
    'crystal palace': ('England', 'Premier League'),
    'fulham': ('England', 'Premier League'),
    'brighton': ('England', 'Premier League'),
    'bournemouth': ('England', 'Premier League'),
    'wolverhampton': ('England', 'Premier League'),
    'wolves': ('England', 'Premier League'),
    'everton': ('England', 'Premier League'),
    'leicester': ('England', 'Premier League'),
    'west ham': ('England', 'Premier League'),
    'ipswich': ('England', 'Premier League'),
    'southampton': ('England', 'Championship'),
    'leeds': ('England', 'Championship'),
    'sunderland': ('England', 'Championship'),
    'charlton': ('England', 'Championship'),
    'derby': ('England', 'Championship'),
    'birmingham': ('England', 'Championship'),
    'stoke': ('England', 'Championship'),
    'bristol city': ('England', 'Championship'),
    'sheffield': ('England', 'Championship'),
    'millwall': ('England', 'Championship'),
    'swansea': ('England', 'Championship'),
    'portsmouth': ('England', 'Championship'),
    'cardiff': ('England', 'Championship'),
    'burnley': ('England', 'Championship'),
    'luton': ('England', 'Championship'),
    'chesterfield': ('England', 'League One'),
    'crewe': ('England', 'League One'),
    'barcelona': ('Spain', 'La Liga'),
    'real madrid': ('Spain', 'La Liga'),
    'atletico madrid': ('Spain', 'La Liga'),
    'atletico': ('Spain', 'La Liga'),
    'villarreal': ('Spain', 'La Liga'),
    'sevilla': ('Spain', 'La Liga'),
    'athletic bilbao': ('Spain', 'La Liga'),
    'real betis': ('Spain', 'La Liga'),
    'betis': ('Spain', 'La Liga'),
    'osasuna': ('Spain', 'La Liga'),
    'mallorca': ('Spain', 'La Liga'),
    'getafe': ('Spain', 'La Liga'),
    'valencia': ('Spain', 'La Liga'),
    'real sociedad': ('Spain', 'La Liga'),
    'girona': ('Spain', 'La Liga'),
    'celta vigo': ('Spain', 'La Liga'),
    'celta': ('Spain', 'La Liga'),
    'oviedo': ('Spain', 'Segunda'),
    'juventus': ('Italy', 'Serie A'),
    'ac milan': ('Italy', 'Serie A'),
    'inter milan': ('Italy', 'Serie A'),
    'inter': ('Italy', 'Serie A'),
    'roma': ('Italy', 'Serie A'),
    'napoli': ('Italy', 'Serie A'),
    'lecce': ('Italy', 'Serie A'),
    'fiorentina': ('Italy', 'Serie A'),
    'atalanta': ('Italy', 'Serie A'),
    'lazio': ('Italy', 'Serie A'),
    'torino': ('Italy', 'Serie A'),
    'udinese': ('Italy', 'Serie A'),
    'bologna': ('Italy', 'Serie A'),
    'empoli': ('Italy', 'Serie A'),
    'cagliari': ('Italy', 'Serie A'),
    'parma': ('Italy', 'Serie A'),
    'monza': ('Italy', 'Serie A'),
    'bayern munich': ('Germany', 'Bundesliga'),
    'bayern': ('Germany', 'Bundesliga'),
    'dortmund': ('Germany', 'Bundesliga'),
    'borussia': ('Germany', 'Bundesliga'),
    'rb leipzig': ('Germany', 'Bundesliga'),
    'leipzig': ('Germany', 'Bundesliga'),
    'bayer leverkusen': ('Germany', 'Bundesliga'),
    'leverkusen': ('Germany', 'Bundesliga'),
    'vfb stuttgart': ('Germany', 'Bundesliga'),
    'stuttgart': ('Germany', 'Bundesliga'),
    'mainz': ('Germany', 'Bundesliga'),
    'wolfsburg': ('Germany', 'Bundesliga'),
    'heidenheim': ('Germany', 'Bundesliga'),
    'union berlin': ('Germany', 'Bundesliga'),
    'eintracht frankfurt': ('Germany', 'Bundesliga'),
    'frankfurt': ('Germany', 'Bundesliga'),
    'freiburg': ('Germany', 'Bundesliga'),
    'augsburg': ('Germany', 'Bundesliga'),
    'werder bremen': ('Germany', 'Bundesliga'),
    'psg': ('France', 'Ligue 1'),
    'paris saint-germain': ('France', 'Ligue 1'),
    'as monaco': ('France', 'Ligue 1'),
    'monaco': ('France', 'Ligue 1'),
    'rennes': ('France', 'Ligue 1'),
    'lorient': ('France', 'Ligue 1'),
    'le havre': ('France', 'Ligue 1'),
    'marseille': ('France', 'Ligue 1'),
    'lyon': ('France', 'Ligue 1'),
    'nice': ('France', 'Ligue 1'),
    'lens': ('France', 'Ligue 1'),
    'lille': ('France', 'Ligue 1'),
    'atlanta united': ('USA', 'MLS'),
    'atlanta': ('USA', 'MLS'),
    'fc cincinnati': ('USA', 'MLS'),
    'cincinnati': ('USA', 'MLS'),
    'new york red bulls': ('USA', 'MLS'),
    'new york city': ('USA', 'MLS'),
    'seattle sounders': ('USA', 'MLS'),
    'portland timbers': ('USA', 'MLS'),
    'la galaxy': ('USA', 'MLS'),
    'inter miami': ('USA', 'MLS'),
    'chicago fire': ('USA', 'MLS'),
    'colorado rapids': ('USA', 'MLS'),
    'dc united': ('USA', 'MLS'),
    'fenerbahce': ('Turkey', 'Super Lig'),
    'fenerbahçe': ('Turkey', 'Super Lig'),
    'galatasaray': ('Turkey', 'Super Lig'),
    'besiktas': ('Turkey', 'Super Lig'),
    'beşiktaş': ('Turkey', 'Super Lig'),
    'kayserispor': ('Turkey', 'Super Lig'),
    'rizespor': ('Turkey', 'Super Lig'),
    'konyaspor': ('Turkey', 'Super Lig'),
    'goztepe': ('Turkey', 'Super Lig'),
    'göztepe': ('Turkey', 'Super Lig'),
    'eyupspor': ('Turkey', 'Super Lig'),
    'eyüpspor': ('Turkey', 'Super Lig'),
    'trabzonspor': ('Turkey', 'Super Lig'),
    'fc utrecht': ('Netherlands', 'Eredivisie'),
    'utrecht': ('Netherlands', 'Eredivisie'),
    'az alkmaar': ('Netherlands', 'Eredivisie'),
    'fc twente': ('Netherlands', 'Eredivisie'),
    'twente': ('Netherlands', 'Eredivisie'),
    'heerenveen': ('Netherlands', 'Eredivisie'),
    'groningen': ('Netherlands', 'Eredivisie'),
    'ajax': ('Netherlands', 'Eredivisie'),
    'psv': ('Netherlands', 'Eredivisie'),
    'feyenoord': ('Netherlands', 'Eredivisie'),
    'excelsior': ('Netherlands', 'Eredivisie'),
    'telstar': ('Netherlands', 'Eredivisie'),
    'krc genk': ('Belgium', 'Pro League'),
    'genk': ('Belgium', 'Pro League'),
    'oh leuven': ('Belgium', 'Pro League'),
    'union saint-gilloise': ('Belgium', 'Pro League'),
    'royal antwerp': ('Belgium', 'Pro League'),
    'antwerp': ('Belgium', 'Pro League'),
    'sint-truiden': ('Belgium', 'Pro League'),
    'dender': ('Belgium', 'Pro League'),
    'anderlecht': ('Belgium', 'Pro League'),
    'club brugge': ('Belgium', 'Pro League'),
    'standard liege': ('Belgium', 'Pro League'),
    'standard': ('Belgium', 'Pro League'),
    'fc porto': ('Portugal', 'Primeira Liga'),
    'porto': ('Portugal', 'Primeira Liga'),
    'sporting cp': ('Portugal', 'Primeira Liga'),
    'sporting': ('Portugal', 'Primeira Liga'),
    'vitoria guimaraes': ('Portugal', 'Primeira Liga'),
    'guimaraes': ('Portugal', 'Primeira Liga'),
    'estoril': ('Portugal', 'Primeira Liga'),
    'benfica': ('Portugal', 'Primeira Liga'),
    'braga': ('Portugal', 'Primeira Liga'),
    'rangers': ('Scotland', 'Scottish Premiership'),
    'celtic': ('Scotland', 'Scottish Premiership'),
    'hearts': ('Scotland', 'Scottish Premiership'),
    'hibernian': ('Scotland', 'Scottish Premiership'),
    'paok': ('Greece', 'Super League'),
    'olympiacos': ('Greece', 'Super League'),
    'panathinaikos': ('Greece', 'Super League'),
    'river plate': ('Argentina', 'Primera División'),
    'boca juniors': ('Argentina', 'Primera División'),
    'racing club': ('Argentina', 'Primera División'),
    'independiente': ('Argentina', 'Primera División'),
    'aldosivi': ('Argentina', 'Primera División'),
    'liverpool montevideo': ('Uruguay', 'Primera División'),
    'juventud de las piedras': ('Uruguay', 'Primera División'),
    'juventud': ('Uruguay', 'Primera División'),
    'penarol': ('Uruguay', 'Primera División'),
    'peñarol': ('Uruguay', 'Primera División'),
    'nacional': ('Uruguay', 'Primera División'),
    'nk osijek': ('Croatia', 'HNL'),
    'osijek': ('Croatia', 'HNL'),
    'nk lokomotiva': ('Croatia', 'HNL'),
    'lokomotiva': ('Croatia', 'HNL'),
    'dinamo zagreb': ('Croatia', 'HNL'),
    'hajduk split': ('Croatia', 'HNL'),
    'cfr cluj': ('Romania', 'Liga 1'),
    'universitatea cluj': ('Romania', 'Liga 1'),
    'fcsb': ('Romania', 'Liga 1'),
    # England - Championship
    'blackpool': ('England', 'Championship'),
    'leyton orient': ('England', 'League One'),
    'preston': ('England', 'Championship'),
    'west brom': ('England', 'Championship'),
    'west bromwich': ('England', 'Championship'),
    'wigan': ('England', 'Championship'),
    'hull city': ('England', 'Championship'),
    'hull': ('England', 'Championship'),
    'oxford united': ('England', 'Championship'),
    'coventry': ('England', 'Championship'),
    'norwich': ('England', 'Championship'),
    'middlesbrough': ('England', 'Championship'),
    'watford': ('England', 'Championship'),
    'qpr': ('England', 'Championship'),
    'queens park rangers': ('England', 'Championship'),
    # Germany
    '1899 hoffenheim': ('Germany', 'Bundesliga'),
    'hoffenheim': ('Germany', 'Bundesliga'),
    'fc st. pauli': ('Germany', '2. Bundesliga'),
    'st. pauli': ('Germany', '2. Bundesliga'),
    'pauli': ('Germany', '2. Bundesliga'),
    'köln': ('Germany', '2. Bundesliga'),
    'koln': ('Germany', '2. Bundesliga'),
    '1. fc köln': ('Germany', '2. Bundesliga'),
    # Spain
    'levante': ('Spain', 'Segunda'),
    'andorra cf': ('Spain', 'Copa del Rey'),
    # Denmark
    'midtjylland': ('Denmark', 'Superliga'),
    'midtylland': ('Denmark', 'Superliga'),
    'viborg': ('Denmark', 'Superliga'),
    'fc nordsjaelland': ('Denmark', 'Superliga'),
    'nordsjaelland': ('Denmark', 'Superliga'),
    'aarhus gf': ('Denmark', 'Superliga'),
    'agf': ('Denmark', 'Superliga'),
    'hillerod': ('Denmark', 'First Division'),
    'hillerød': ('Denmark', 'First Division'),
    'lyngby': ('Denmark', 'First Division'),
    'aarhus fremad': ('Denmark', 'First Division'),
    'hobro': ('Denmark', 'First Division'),
    # Poland
    'lechia gdansk': ('Poland', 'Ekstraklasa'),
    'wisla plock': ('Poland', 'Ekstraklasa'),
    'radomiak': ('Poland', 'Ekstraklasa'),
    'piast gliwice': ('Poland', 'Ekstraklasa'),
    'lech poznan': ('Poland', 'Ekstraklasa'),
    # Norway
    'sandnes ulf': ('Norway', 'Eliteserien'),
    'stromsgodset': ('Norway', 'Eliteserien'),
    'aalesunds': ('Norway', 'Eliteserien'),
    'aalesund': ('Norway', 'Eliteserien'),
    'kristiansund': ('Norway', 'Eliteserien'),
    'lyn': ('Norway', 'Eliteserien'),
    'moss': ('Norway', '2. Division'),
    # Sweden
    'sirius': ('Sweden', 'Allsvenskan'),
    'hammarby': ('Sweden', 'Allsvenskan'),
    # Bulgaria
    'slavia sofia': ('Bulgaria', 'First Professional League'),
    'botev vratsa': ('Bulgaria', 'First Professional League'),
    'botev': ('Bulgaria', 'First Professional League'),
    'ludogorets': ('Bulgaria', 'First Professional League'),
    # Slovakia
    'tatran presov': ('Slovakia', 'Super Liga'),
    'trencin': ('Slovakia', 'Super Liga'),
    # Brazil
    'corinthians': ('Brazil', 'Brasileirao'),
    'vasco da gama': ('Brazil', 'Brasileirao'),
    'gremio': ('Brazil', 'Brasileirao'),
    'grêmio': ('Brazil', 'Brasileirao'),
    'coritiba': ('Brazil', 'Brasileirao'),
    'flamengo': ('Brazil', 'Brasileirao'),
    'palmeiras': ('Brazil', 'Brasileirao'),
    'sao paulo': ('Brazil', 'Brasileirao'),
    'santos': ('Brazil', 'Brasileirao'),
    'atletico mineiro': ('Brazil', 'Brasileirao'),
    # Argentina
    'ca platense': ('Argentina', 'Primera División'),
    'platense': ('Argentina', 'Primera División'),
    'san lorenzo': ('Argentina', 'Primera División'),
    'huracan': ('Argentina', 'Primera División'),
    'talleres': ('Argentina', 'Primera División'),
    'estudiantes': ('Argentina', 'Primera División'),
    # Uruguay
    'cerro largo': ('Uruguay', 'Primera División'),
    'racing club uru': ('Uruguay', 'Primera División'),
    # Scotland
    'dundee utd': ('Scotland', 'Scottish Premiership'),
    'dundee united': ('Scotland', 'Scottish Premiership'),
    'dundee': ('Scotland', 'Scottish Premiership'),
    'aberdeen': ('Scotland', 'Scottish Premiership'),
    'motherwell': ('Scotland', 'Scottish Premiership'),
    'st mirren': ('Scotland', 'Scottish Premiership'),
    # Bosnia
    'zrinjski': ('Bosnia', 'Premier League'),
    'radnik bijeljina': ('Bosnia', 'Premier League'),
    # Czech Republic
    'banik ostrava': ('Czech Republic', 'Czech Liga'),
    'sfc opava': ('Czech Republic', 'Czech Liga'),
    'slavia prague': ('Czech Republic', 'Czech Liga'),
    'sparta prague': ('Czech Republic', 'Czech Liga'),
    # Georgia
    'dinamo tbilisi': ('Georgia', 'Erovnuli Liga'),
    # Turkey (extra)
    'antalyaspor': ('Turkey', 'Super Lig'),
    'gaziantep': ('Turkey', 'Super Lig'),
    # International Women's
    'sweden (w)': ('International', "Women's"),
    'denmark (w)': ('International', "Women's"),
    'faroe islands (w)': ('International', "Women's"),
    'greece (w)': ('International', "Women's"),
    'serbia u19 (w)': ('International', "Women's"),
    'iceland u19 (w)': ('International', "Women's"),
}

PDF_LEAGUE_MAP = {
    'UEFA Champions League': ('Europe', 'Champions League'),
    'UEFA Europa League': ('Europe', 'Europa League'),
    'UEFA Europa Conference League': ('Europe', 'Conference League'),
    'UEFA Conference League': ('Europe', 'Conference League'),
    'Premier League': ('England', 'Premier League'),
    'Championship': ('England', 'Championship'),
    'League One': ('England', 'League One'),
    'League Two': ('England', 'League Two'),
    'La Liga': ('Spain', 'La Liga'),
    'Segunda División': ('Spain', 'Segunda'),
    'Bundesliga': ('Germany', 'Bundesliga'),
    '2. Bundesliga': ('Germany', '2. Bundesliga'),
    'Serie A': ('Italy', 'Serie A'),
    'Ligue 1': ('France', 'Ligue 1'),
    'Süper Lig': ('Turkey', 'Super Lig'),
    'Super Lig': ('Turkey', 'Super Lig'),
    'Jupiler Pro League': ('Belgium', 'Pro League'),
    'Eredivisie': ('Netherlands', 'Eredivisie'),
    'Primeira Liga': ('Portugal', 'Primeira Liga'),
    'Scottish Premiership': ('Scotland', 'Scottish Premiership'),
    'MLS': ('USA', 'MLS'),
    'Super League': ('Greece', 'Super League'),
    'Liga 1': ('Romania', 'Liga 1'),
    'HNL': ('Croatia', 'HNL'),
    'Primera División': ('Argentina', 'Primera División'),
    'Primera Division': ('Argentina', 'Primera División'),
}

def get_country_league(match):
    """Detect country and league from match name using team mapping."""
    match_lower = match.lower()
    for team in sorted(TEAM_MAP.keys(), key=len, reverse=True):
        if team in match_lower:
            return TEAM_MAP[team]
    if '(w)' in match_lower:
        return "Women's", "Women's Football"
    if 'u19' in match_lower or 'u-19' in match_lower:
        return 'Youth', 'U19'
    if 'u21' in match_lower or 'u-21' in match_lower:
        return 'Youth', 'U21'
    if 'u23' in match_lower or 'u-23' in match_lower:
        return 'Youth', 'U23'
    return 'Other', 'Other'

def get_country_league_pdf(league_text, match):
    """Detect country/league using explicit PDF league text first, then team mapping."""
    for league_name, (country, league) in sorted(PDF_LEAGUE_MAP.items(), key=lambda x: -len(x[0])):
        if league_name.lower() in league_text.lower():
            return country, league
    return get_country_league(match)

def calc_odds(pnl, stake, bet_type=''):
    """Return odds: exact for wins, estimated from bet type for losses."""
    try:
        pnl = float(pnl or 0)
        stake = float(stake or 0)
    except Exception:
        pnl, stake = 0.0, 0.0
    if stake > 0 and pnl > 0:
        return round((pnl + stake) / stake, 3)
    bt = str(bet_type or '').lower()
    if '3.5' in bt:
        return 2.20
    if '2.5' in bt:
        return 1.80
    if '1.5' in bt:
        return 1.55
    if '0.5' in bt:
        return 1.35
    return 1.50

# ==================== DATABASE ====================

def init_db():
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
        source TEXT DEFAULT 'csv',
        odds REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    for col, definition in [('source', 'TEXT DEFAULT "csv"'), ('odds', 'REAL')]:
        try:
            c.execute(f'ALTER TABLE bets ADD COLUMN {col} {definition}')
        except Exception:
            pass
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def db_insert_bet(bet, source='csv'):
    """Insert bet if not a duplicate. Returns True if inserted."""
    conn = get_db()
    c = conn.cursor()
    date_day = str(bet.get('date', ''))[:10]
    c.execute(
        'SELECT id FROM bets WHERE date LIKE ? AND match = ? AND bet_type = ?',
        (date_day + '%', bet.get('match', ''), bet.get('bet_type', ''))
    )
    if c.fetchone():
        conn.close()
        return False
    odds = bet.get('odds') or calc_odds(bet.get('pnl', 0), bet.get('stake', 0), bet.get('bet_type', ''))
    c.execute(
        '''INSERT INTO bets (date, match, bet_type, market, stake, matched, status, pnl, country, league, source, odds)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (bet.get('date', ''), bet.get('match', ''), bet.get('bet_type', ''),
         bet.get('market', ''), bet.get('stake', 0), bet.get('matched', 0),
         bet.get('status', ''), bet.get('pnl', 0),
         bet.get('country', ''), bet.get('league', ''), source, odds)
    )
    conn.commit()
    conn.close()
    return True

def db_load_all():
    """Load all bets from database ordered by date descending."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM bets ORDER BY date DESC')
    rows = c.fetchall()
    conn.close()
    keys = ['id', 'date', 'match', 'bet_type', 'market', 'stake', 'matched', 'status', 'pnl', 'country', 'league', 'source', 'odds']
    records = []
    for row in rows:
        r = {}
        for k in keys:
            try:
                r[k] = row[k]
            except Exception:
                r[k] = None
        # Fill in odds if missing (old records before column was added)
        if r['odds'] is None:
            r['odds'] = calc_odds(r.get('pnl', 0), r.get('stake', 0), r.get('bet_type', ''))
        records.append(r)
    return records

def db_remove_duplicates():
    """Remove duplicates keeping the earliest record."""
    conn = get_db()
    c = conn.cursor()
    c.execute('''DELETE FROM bets WHERE id NOT IN (
        SELECT MIN(id) FROM bets GROUP BY date, match, bet_type
    )''')
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted

# ==================== DATA LOADING ====================

def load_csv_data(filepath):
    """Import CSV into database. Returns count of new records added."""
    try:
        df = pd.read_csv(filepath)
        added = 0
        for _, row in df.iterrows():
            # Skip summary/non-data rows (e.g. 'Period' summary row at bottom)
            placed = str(row.get('Placed', '') or '')
            if not re.match(r'\d{4}-\d{2}-\d{2}', placed):
                continue
            try:
                pnl = float(row.get('P&L', 0) or 0)
            except Exception:
                pnl = 0
            try:
                stake = float(row.get('Stake requested', 0) or 0)
            except Exception:
                stake = 0
            try:
                matched = float(row.get('Matched', 0) or 0)
            except Exception:
                matched = 0
            match = str(row.get('Match', ''))
            country, league = get_country_league(match)
            bet = {
                'date': placed,
                'match': match,
                'bet_type': str(row.get('Bet Type', '')),
                'market': str(row.get('Market', '')),
                'stake': stake,
                'matched': matched,
                'status': str(row.get('Status', '')),
                'pnl': pnl,
                'country': country,
                'league': league,
            }
            if db_insert_bet(bet, source='csv'):
                added += 1
        return added
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return 0

def extract_leagues(records):
    """Return sorted list of unique league dicts from records."""
    seen = {}
    for r in records:
        country = r.get('country') or ''
        league = r.get('league') or ''
        if not country or not league or country in ('Other', 'Unknown') or league in ('Other', 'Unknown'):
            continue
        key = f"{country} - {league}"
        if key not in seen:
            seen[key] = {'country': country, 'league': league, 'label': key}
    return sorted(seen.values(), key=lambda x: (x['country'], x['league']))

def normalize_bet_type(bt):
    """Strip 'Back ' prefix to normalize bet type labels."""
    bt = (bt or '').strip()
    if bt.lower().startswith('back '):
        bt = bt[5:]
    return bt

def extract_markets(records):
    """Return sorted list of unique bet types (normalized) from records."""
    seen = set()
    for r in records:
        bt = normalize_bet_type(r.get('bet_type') or '')
        if bt and bt.lower() not in ('', 'unknown', 'n/a', 'other'):
            seen.add(bt)
    return sorted(seen)

def reenrich_leagues():
    """Re-map country/league for existing DB records that are Other/Unknown."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, match FROM bets WHERE country IN ('Other','Unknown') OR league IN ('Other','Unknown') OR country IS NULL OR league IS NULL")
    rows = c.fetchall()
    updated = 0
    for row in rows:
        match = row[1] or ''
        country, league = get_country_league(match)
        if country != 'Other' or league != 'Other':
            c.execute("UPDATE bets SET country=?, league=? WHERE id=?", (country, league, row[0]))
            updated += 1
    conn.commit()
    conn.close()
    return updated

def save_config(config):
    """Persist config to SQLite so it survives restarts."""
    try:
        import json
        conn = get_db()
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS app_config (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("INSERT OR REPLACE INTO app_config (key, value) VALUES ('main', ?)", (json.dumps(config),))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving config: {e}")

def load_config():
    """Load persisted config from SQLite, returning empty dict if none saved."""
    try:
        import json
        conn = get_db()
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS app_config (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("SELECT value FROM app_config WHERE key = 'main'")
        row = c.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except Exception:
        pass
    return {}

# ==================== PDF PROCESSING ====================

def parse_pdf(pdf_path):
    """
    Parse BetsoccerPro PDF. Each bet is two consecutive lines:
      Line 1: "Team A vs Team B"
      Line 2: "{League} {Bet Type} {Odds} {Win|Loss} {DD/MM/YYYY} {time} {units}"
    """
    try:
        import pdfplumber
    except ImportError:
        return [], "pdfplumber not installed. Run: pip install pdfplumber"

    bets = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                i = 0
                while i < len(lines):
                    line = lines[i]
                    # Skip column header row
                    if 'Bet Type' in line and 'Odds' in line and 'Result' in line:
                        i += 1
                        continue
                    # Match line: must contain " vs " and NOT contain Win/Loss/date
                    if ' vs ' in line and not re.search(r'\b(Win|Loss)\b', line) and not re.search(r'\d{2}/\d{2}/\d{4}', line):
                        match_name = line
                        if i + 1 >= len(lines):
                            i += 1
                            continue
                        detail = lines[i + 1]
                        # Must have a DD/MM/YYYY date in the detail line
                        date_m = re.search(r'(\d{2}/\d{2}/\d{4})', detail)
                        if not date_m:
                            i += 1
                            continue
                        try:
                            bet_date = datetime.strptime(date_m.group(1), '%d/%m/%Y').strftime('%Y-%m-%d')
                        except Exception:
                            i += 2
                            continue
                        # Result: Win or Loss before the date
                        result_m = re.search(r'\b(Win|Loss)\b', detail[:date_m.start()])
                        if not result_m:
                            i += 2
                            continue
                        is_win = result_m.group(1) == 'Win'
                        # Odds: float immediately before Win/Loss
                        odds_m = re.search(r'(\d+\.?\d*)\s+(?:Win|Loss)', detail)
                        odds = float(odds_m.group(1)) if odds_m else 1.5
                        # Bet type
                        bt_m = re.search(r'(Back Over|Over|Back Under|Under)\s+[\d.]+\s+Goals?', detail)
                        bet_type = bt_m.group(0) if bt_m else 'Unknown'
                        # League text (everything before the bet type in the detail line)
                        league_text = detail[:bt_m.start()].strip() if bt_m else ''
                        country, league = get_country_league_pdf(league_text, match_name)
                        stake = 30.0
                        pnl = round((odds - 1) * stake, 2) if is_win else -stake
                        bets.append({
                            'date': bet_date,
                            'match': match_name,
                            'bet_type': bet_type,
                            'market': 'Live',
                            'stake': stake,
                            'matched': stake,
                            'status': 'Settled',
                            'pnl': pnl,
                            'country': country,
                            'league': league,
                            'odds': odds,
                        })
                        i += 2
                        continue
                    i += 1
    except Exception as e:
        return [], str(e)
    return bets, None

# ==================== ANALYSIS ENGINE ====================

def run_analysis(records, config):
    # --- Date filter ---
    date_start = config.get('date_start') or None
    date_end = config.get('date_end') or None
    if date_start or date_end:
        filtered = []
        for r in records:
            ds = str(r.get('date', ''))[:10]
            if date_start and ds < date_start:
                continue
            if date_end and ds > date_end:
                continue
            filtered.append(r)
        records = filtered

    # --- Time-of-day filter (HH:MM format; only applies to records that have a time component) ---
    time_start = config.get('time_start') or None
    time_end = config.get('time_end') or None
    if time_start or time_end:
        filtered = []
        for r in records:
            date_str = str(r.get('date', ''))
            time_part = date_str[11:16] if len(date_str) >= 16 else None
            if time_part is None:
                # No time info — include regardless of filter
                filtered.append(r)
                continue
            if time_start and time_part < time_start:
                continue
            if time_end and time_part > time_end:
                continue
            filtered.append(r)
        records = filtered

    # --- League filter ---
    selected_leagues = config.get('selected_leagues') or []
    if selected_leagues:
        def _league_label(r):
            return f"{r.get('country', '')} - {r.get('league', '')}"
        def _is_unmapped(r):
            c, lg = r.get('country', ''), r.get('league', '')
            return not c or not lg or c in ('Other', 'Unknown') or lg in ('Other', 'Unknown')
        records = [r for r in records
                   if _league_label(r) in selected_leagues or _is_unmapped(r)]

    # --- Market filter (uses normalized bet_type, not the 'market' channel column) ---
    selected_markets = config.get('selected_markets') or []
    if selected_markets:
        records = [r for r in records
                   if normalize_bet_type(r.get('bet_type') or '') in selected_markets]

    # --- Odds filter ---
    min_odds = float(config.get('odds_min', 1.0))
    max_odds = float(config.get('odds_max', 100.0))
    if min_odds > 1.0 or max_odds < 100.0:
        filtered = []
        for r in records:
            o = float(r.get('odds') or calc_odds(r.get('pnl', 0), r.get('stake', 0), r.get('bet_type', '')))
            if min_odds <= o <= max_odds:
                filtered.append(r)
        records = filtered

    strategy = config.get('staking_strategy', 'flat')
    daily_bank = float(config.get('daily_bank', 1000))
    stake_pct = float(config.get('stake_percentage', 2))
    base_stake = float(config.get('base_stake', 20))
    commission = float(config.get('commission', 0)) / 100.0  # e.g. 0.02 for 2%

    results = {
        'total_bets': 0, 'won': 0, 'lost': 0, 'void': 0,
        'total_stake': 0.0, 'total_pnl': 0.0,
        'roi': 0.0, 'win_rate': 0.0,
        'daily_results': [], 'weekly_results': [], 'league_breakdown': [],
    }

    current_bank = daily_bank
    processed_bets = []
    loss_streak = 0
    daily_summary = {}

    from collections import defaultdict
    date_groups = defaultdict(list)
    for record in sorted(records, key=lambda r: str(r.get('date', ''))):
        status = str(record.get('status', '')).strip()
        if status not in ('Settled', 'WON', 'LOST'):
            continue
        date_key = str(record.get('date', ''))[:10]
        date_groups[date_key].append(record)

    fib_seq = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]

    for date_key in sorted(date_groups.keys()):
        day_start_bank = current_bank

        # Compounding: all bets this day share the same stake (end-of-previous-day bank).
        # Fibonacci: opening stake for the day shown in summary; actual stake updates per-bet.
        if strategy == 'compounding':
            day_stake = round(current_bank * (stake_pct / 100), 2)
            stake_per_bet_display = day_stake
        elif strategy == 'flat':
            day_stake = base_stake
            stake_per_bet_display = base_stake
        else:
            day_stake = None
            stake_per_bet_display = round(base_stake * fib_seq[min(loss_streak, len(fib_seq) - 1)], 2)

        day_bets = day_won = day_lost = 0
        day_pnl = day_staked = 0.0

        for record in date_groups[date_key]:
            try:
                hist_pnl = float(record.get('pnl', 0) or 0)
            except Exception:
                hist_pnl = 0
            if pd.isna(hist_pnl):
                hist_pnl = 0

            if strategy == 'fibonacci':
                stake = base_stake * fib_seq[min(loss_streak, len(fib_seq) - 1)]
            else:
                stake = day_stake

            # P&L uses real odds + scenario stake + commission.
            # CSV amount is NOT used — only win/loss result and odds.
            odds = float(record.get('odds') or calc_odds(hist_pnl, record.get('stake', 0), record.get('bet_type', '')))
            if hist_pnl > 0:
                gross_win = stake * (odds - 1)
                pnl = round(gross_win * (1.0 - commission), 2)
            elif hist_pnl < 0:
                pnl = -round(stake, 2)
            else:
                pnl = 0.0

            results['total_bets'] += 1
            results['total_stake'] += stake
            day_bets += 1
            day_staked += stake

            if pnl > 0:
                results['won'] += 1
                current_bank += pnl
                loss_streak = 0
                day_won += 1
            elif pnl < 0:
                results['lost'] += 1
                current_bank += pnl
                loss_streak += 1
                day_lost += 1
            else:
                results['void'] += 1
                loss_streak = 0

            results['total_pnl'] += pnl
            day_pnl += pnl
            processed_bets.append({**record, 'calculated_stake': stake, 'scaled_pnl': pnl, 'bank_after': current_bank})

        daily_summary[date_key] = {
            'bets': day_bets,
            'won': day_won,
            'lost': day_lost,
            'pnl': round(day_pnl, 2),
            'staked': round(day_staked, 2),
            'start_bank': round(day_start_bank, 2),
            'stake_per_bet': round(stake_per_bet_display, 2),
            'end_bank': round(current_bank, 2),
        }

    if results['total_stake'] > 0:
        results['roi'] = (results['total_pnl'] / results['total_stake']) * 100
    if results['total_bets'] > 0:
        results['win_rate'] = (results['won'] / results['total_bets']) * 100

    results['daily_results'] = [{'date': k, **v} for k, v in sorted(daily_summary.items())]

    # Weekly breakdown — built from daily_summary so start/end bank flow naturally
    weekly_summary = {}
    for date_key, day in sorted(daily_summary.items()):
        try:
            dt = datetime.strptime(date_key, '%Y-%m-%d')
            wk = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
            if wk not in weekly_summary:
                weekly_summary[wk] = {
                    'bets': 0, 'won': 0, 'lost': 0, 'pnl': 0.0, 'staked': 0.0,
                    'start_bank': day['start_bank'],
                    'end_bank': 0.0,
                }
            weekly_summary[wk]['bets'] += day['bets']
            weekly_summary[wk]['won'] += day['won']
            weekly_summary[wk]['lost'] += day['lost']
            weekly_summary[wk]['pnl'] = round(weekly_summary[wk]['pnl'] + day['pnl'], 2)
            weekly_summary[wk]['staked'] += day['staked']
            weekly_summary[wk]['end_bank'] = day['end_bank']
        except Exception:
            pass
    results['weekly_results'] = [{'week': k, **v} for k, v in sorted(weekly_summary.items())]

    # League breakdown
    league_summary = {}
    for bet in processed_bets:
        key = f"{bet.get('country', 'Other')} - {bet.get('league', 'Other')}"
        if key not in league_summary:
            league_summary[key] = {'bets': 0, 'won': 0, 'lost': 0, 'pnl': 0.0}
        league_summary[key]['bets'] += 1
        bp = float(bet.get('scaled_pnl', 0) or 0)
        if bp > 0:
            league_summary[key]['won'] += 1
        elif bp < 0:
            league_summary[key]['lost'] += 1
        league_summary[key]['pnl'] += bp
    for key, v in league_summary.items():
        v['win_rate'] = round((v['won'] / v['bets']) * 100, 1) if v['bets'] > 0 else 0
    results['league_breakdown'] = [
        {'league': k, **v} for k, v in sorted(league_summary.items(), key=lambda x: -x[1]['bets'])
    ]

    results['final_bank'] = current_bank
    results['strategy'] = strategy
    return results

# ==================== ROUTES ====================

@app.route('/')
def index():
    records = data_store.get('data') or []
    leagues = data_store.get('leagues', [])
    markets = data_store.get('markets', [])
    dates = sorted(str(r.get('date', ''))[:10] for r in records if r.get('date'))
    dates = [d for d in dates if d]
    return render_template('index.html',
                           config=data_store['config'],
                           leagues=leagues,
                           markets=markets,
                           record_count=len(records),
                           date_min=dates[0] if dates else '',
                           date_max=dates[-1] if dates else '')

@app.route('/data')
def data_page():
    records = data_store.get('data') or []
    return render_template('data.html', records=records)

@app.route('/analysis')
def analysis_page():
    results = data_store.get('results') or {}
    leagues = data_store.get('leagues', [])
    markets = data_store.get('markets', [])
    records = data_store.get('data') or []
    dates = sorted(str(r.get('date', ''))[:10] for r in records if r.get('date'))
    dates = [d for d in dates if d]
    return render_template('analysis.html',
                           results=results,
                           config=data_store['config'],
                           leagues=leagues,
                           markets=markets,
                           date_min=dates[0] if dates else '',
                           date_max=dates[-1] if dates else '')

@app.route('/settings')
def settings_page():
    records = data_store.get('data') or []
    return render_template('settings.html', config=data_store['config'], record_count=len(records))

# ==================== API ====================

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(data_store['config'])

@app.route('/api/config', methods=['POST'])
def update_config():
    data_store['config'].update(request.json or {})
    save_config(data_store['config'])
    return jsonify({'success': True, 'config': data_store['config']})

@app.route('/api/leagues', methods=['GET'])
def get_leagues():
    return jsonify({'leagues': data_store['leagues']})

@app.route('/api/analyze', methods=['POST'])
def run_analysis_api():
    config = request.json or {}
    data_store['config'].update(config)
    save_config(data_store['config'])
    records = data_store.get('data') or []
    if not records:
        return jsonify({'error': 'No data loaded'}), 400
    results = run_analysis(records, data_store['config'])
    data_store['results'] = results
    return jsonify(results)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Please upload a CSV file'}), 400
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)
    added = load_csv_data(filepath)
    records = db_load_all()
    data_store['data'] = records
    data_store['leagues'] = extract_leagues(records)
    data_store['markets'] = extract_markets(records)
    return jsonify({'success': True, 'added': added, 'total': len(records), 'leagues': data_store['leagues']})

@app.route('/api/process-pdf', methods=['POST'])
def process_pdf_api():
    base_path = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(base_path, 'BetsoccerPro Results April.pdf')
    if not os.path.exists(pdf_path):
        return jsonify({'error': 'PDF not found at expected path'}), 404
    bets, error = parse_pdf(pdf_path)
    if error:
        return jsonify({'error': error}), 500
    # Remove old PDF records and re-import cleanly
    conn = get_db()
    conn.execute("DELETE FROM bets WHERE source = 'pdf'")
    conn.commit()
    conn.close()
    added = sum(1 for bet in bets if db_insert_bet(bet, source='pdf'))
    records = db_load_all()
    data_store['data'] = records
    data_store['leagues'] = extract_leagues(records)
    data_store['markets'] = extract_markets(records)
    return jsonify({'success': True, 'extracted': len(bets), 'added': added, 'total': len(records)})

@app.route('/api/data/summary')
def data_summary():
    records = data_store.get('data') or []
    if not records:
        return jsonify({'summary': None})
    dates = sorted(str(r.get('date', ''))[:10] for r in records if r.get('date'))
    dates = [d for d in dates if d]
    return jsonify({'summary': {
        'total_records': len(records),
        'date_range': {'start': dates[0] if dates else '', 'end': dates[-1] if dates else ''},
        'leagues': data_store.get('leagues', []),
    }})

@app.route('/api/deduplicate', methods=['POST'])
def deduplicate_api():
    deleted = db_remove_duplicates()
    records = db_load_all()
    data_store['data'] = records
    data_store['leagues'] = extract_leagues(records)
    data_store['markets'] = extract_markets(records)
    return jsonify({'success': True, 'deleted': deleted, 'remaining': len(records)})

@app.route('/api/delete', methods=['POST'])
def delete_records_api():
    ids = request.json.get('ids', [])
    if not ids:
        return jsonify({'error': 'No IDs provided'}), 400
    conn = get_db()
    c = conn.cursor()
    placeholders = ','.join(['?' for _ in ids])
    c.execute(f'DELETE FROM bets WHERE id IN ({placeholders})', ids)
    deleted = c.rowcount
    conn.commit()
    conn.close()
    records = db_load_all()
    data_store['data'] = records
    data_store['leagues'] = extract_leagues(records)
    data_store['markets'] = extract_markets(records)
    return jsonify({'success': True, 'deleted': deleted, 'remaining': len(records)})

# ==================== INIT ====================

def db_cleanup_bad_records():
    """Remove records with invalid/placeholder dates (e.g. '2026-01-01' fallback, 'Period')."""
    conn = get_db()
    c = conn.cursor()
    # Delete obvious placeholder/fallback dates and non-date values
    c.execute("DELETE FROM bets WHERE date = '2026-01-01'")
    c.execute("DELETE FROM bets WHERE date NOT LIKE '20__-__-__%'")
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted

def initialize_app():
    init_db()
    # Load persisted config so settings survive server restarts
    saved = load_config()
    if saved:
        data_store['config'].update(saved)
        print("Loaded saved config from database")
    # Clean up any bad records from old parser runs
    cleaned = db_cleanup_bad_records()
    if cleaned:
        print(f"Removed {cleaned} bad records from database")
    base_path = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_path, 'betsoccer_history_20260401_20260509.csv')
    if os.path.exists(csv_path):
        added = load_csv_data(csv_path)
        if added > 0:
            print(f"Imported {added} new records from CSV")
    db_remove_duplicates()
    # Re-enrich any records that are still Other/Unknown with updated TEAM_MAP
    enriched = reenrich_leagues()
    if enriched:
        print(f"Re-enriched {enriched} records with league data")
    records = db_load_all()
    data_store['data'] = records
    data_store['leagues'] = extract_leagues(records)
    data_store['markets'] = extract_markets(records)
    print(f"Loaded {len(records)} records, {len(data_store['leagues'])} leagues, {len(data_store['markets'])} markets detected")

initialize_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
