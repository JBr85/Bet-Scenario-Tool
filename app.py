from flask import Flask, render_template, request, jsonify
import pandas as pd
import sqlite3
import os
import re
import math
import json
import difflib
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

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
        'selected_sources': [],
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
    'nottm forest': ('England', 'Premier League'),
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
    'atlético madrid': ('Spain', 'La Liga'),
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
    'paris st-g': ('France', 'Ligue 1'),
    'paris sg': ('France', 'Ligue 1'),
    'as monaco': ('France', 'Ligue 1'),
    'monaco': ('France', 'Ligue 1'),
    'rennes': ('France', 'Ligue 1'),
    'lorient': ('France', 'Ligue 1'),
    'le havre': ('France', 'Ligue 1'),
    'guingamp': ('France', 'Ligue 2'),
    'bastia': ('France', 'Ligue 2'),
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
    'basaksehir': ('Turkey', 'Super Lig'),
    'başakşehir': ('Turkey', 'Super Lig'),
    'istanbul basaksehir': ('Turkey', 'Super Lig'),
    'fatih karagumruk': ('Turkey', 'Super Lig'),
    'fatih karagümrük': ('Turkey', 'Super Lig'),
    'samsunspor': ('Turkey', 'Super Lig'),
    'hatayspor': ('Turkey', 'Super Lig'),
    'alanyaspor': ('Turkey', 'Super Lig'),
    'sivasspor': ('Turkey', 'Super Lig'),
    'kasimpasa': ('Turkey', 'Super Lig'),
    'kasımpaşa': ('Turkey', 'Super Lig'),
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
    'pec zwolle': ('Netherlands', 'Eredivisie'),
    'heracles': ('Netherlands', 'Eredivisie'),
    'heracles almelo': ('Netherlands', 'Eredivisie'),
    'nec nijmegen': ('Netherlands', 'Eredivisie'),
    'nec': ('Netherlands', 'Eredivisie'),
    'roda jc': ('Netherlands', 'Eredivisie'),
    'almere city': ('Netherlands', 'Eredivisie'),
    'go ahead eagles': ('Netherlands', 'Eredivisie'),
    'fortuna sittard': ('Netherlands', 'Eredivisie'),
    'sparta rotterdam': ('Netherlands', 'Eredivisie'),
    'willem ii': ('Netherlands', 'Eredivisie'),
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
    'defensor sporting': ('Uruguay', 'Primera División'),
    'club nacional': ('Uruguay', 'Primera División'),       # Club Nacional de Football (Montevideo)
    'nacional de football': ('Uruguay', 'Primera División'),
    'nacional': ('Portugal', 'Primeira Liga'),              # CD Nacional (Madeira) — appears in all PDF data
    'libertad': ('Paraguay', 'Primera División'),
    'nk osijek': ('Croatia', 'HNL'),
    'osijek': ('Croatia', 'HNL'),
    'nk lokomotiva': ('Croatia', 'HNL'),
    'lokomotiva': ('Croatia', 'HNL'),
    'dinamo zagreb': ('Croatia', 'HNL'),
    'hajduk split': ('Croatia', 'HNL'),
    'cfr cluj': ('Romania', 'Liga 1'),
    'universitatea cluj': ('Romania', 'Liga 1'),
    'fcsb': ('Romania', 'Liga 1'),
    'metaloglobus': ('Romania', 'Liga 1'),
    'slobozia': ('Romania', 'Liga 1'),
    'rapid bucuresti': ('Romania', 'Liga 1'),
    'dinamo bucuresti': ('Romania', 'Liga 1'),
    'u craiova': ('Romania', 'Liga 1'),
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
    'racing club (uru)': ('Uruguay', 'Primera División'),
    'red bull bragantino': ('Brazil', 'Brasileirao'),
    'rb bragantino': ('Brazil', 'Brasileirao'),
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
    # Sweden - Allsvenskan
    'aik': ('Sweden', 'Allsvenskan'),
    'malmo ff': ('Sweden', 'Allsvenskan'),
    'malmö ff': ('Sweden', 'Allsvenskan'),
    'mjallby': ('Sweden', 'Allsvenskan'),
    'halmstads': ('Sweden', 'Allsvenskan'),
    'djurgarden': ('Sweden', 'Allsvenskan'),
    'djurgårdens': ('Sweden', 'Allsvenskan'),
    'ifk goteborg': ('Sweden', 'Allsvenskan'),
    'ifk göteborg': ('Sweden', 'Allsvenskan'),
    'hacken': ('Sweden', 'Allsvenskan'),
    'bk hacken': ('Sweden', 'Allsvenskan'),
    'elfsborg': ('Sweden', 'Allsvenskan'),
    'kalmar': ('Sweden', 'Allsvenskan'),
    'norrkoping': ('Sweden', 'Allsvenskan'),
    'norrköping': ('Sweden', 'Allsvenskan'),
    'vasalunds': ('Sweden', 'Allsvenskan'),
    'vasteras': ('Sweden', 'Allsvenskan'),
    # Brazil - Brasileirao (extra)
    'fluminense': ('Brazil', 'Brasileirao'),
    'chapecoense': ('Brazil', 'Brasileirao'),
    'internacional de bogotá': ('Colombia', 'Liga DIMAYOR'),
    'internacional de bogota': ('Colombia', 'Liga DIMAYOR'),
    'internacional de bogot':  ('Colombia', 'Liga DIMAYOR'),  # garbled-encoding fallback
    'internacional': ('Brazil', 'Brasileirao'),
    'atletico goianiense': ('Brazil', 'Brasileirao'),
    'fortaleza': ('Brazil', 'Brasileirao'),
    'bahia': ('Brazil', 'Brasileirao'),
    'cruzeiro': ('Brazil', 'Brasileirao'),
    'botafogo': ('Brazil', 'Brasileirao'),
    'ceara': ('Brazil', 'Brasileirao'),
    # Argentina - extra
    'banfield': ('Argentina', 'Primera División'),
    'atl tucuman': ('Argentina', 'Primera División'),
    'atletico tucuman': ('Argentina', 'Primera División'),
    'newells old boys': ('Argentina', 'Primera División'),
    'rosario central': ('Argentina', 'Primera División'),
    'velez sarsfield': ('Argentina', 'Primera División'),
    'lanus': ('Argentina', 'Primera División'),
    'tigre': ('Argentina', 'Primera División'),
    'godoy cruz': ('Argentina', 'Primera División'),
    'defensa y justicia': ('Argentina', 'Primera División'),
    'gimnasia': ('Argentina', 'Primera División'),
    # USA - MLS extra
    'nashville sc': ('USA', 'MLS'),
    'austin fc': ('USA', 'MLS'),
    'charlotte fc': ('USA', 'MLS'),
    'minnesota united': ('USA', 'MLS'),
    'sporting kc': ('USA', 'MLS'),
    'real salt lake': ('USA', 'MLS'),
    'new england revolution': ('USA', 'MLS'),
    'toronto fc': ('USA', 'MLS'),
    'cf montreal': ('USA', 'MLS'),
    'vancouver whitecaps': ('USA', 'MLS'),
    'san jose earthquakes': ('USA', 'MLS'),
    'houston dynamo': ('USA', 'MLS'),
    # Mexico
    'tigres': ('Mexico', 'Liga MX'),
    'tigres uanl': ('Mexico', 'Liga MX'),
    'chivas': ('Mexico', 'Liga MX'),
    'guadalajara': ('Mexico', 'Liga MX'),
    'america': ('Mexico', 'Liga MX'),
    'club america': ('Mexico', 'Liga MX'),
    'pumas': ('Mexico', 'Liga MX'),
    'cruz azul': ('Mexico', 'Liga MX'),
    'monterrey': ('Mexico', 'Liga MX'),
    # Colombia - Liga DIMAYOR
    'atletico nacional': ('Colombia', 'Liga DIMAYOR'),
    'atletico nacional medellin': ('Colombia', 'Liga DIMAYOR'),
    'once caldas': ('Colombia', 'Liga DIMAYOR'),
    'deportivo cali': ('Colombia', 'Liga DIMAYOR'),
    'santa fe': ('Colombia', 'Liga DIMAYOR'),
    'millonarios': ('Colombia', 'Liga DIMAYOR'),
    'junior': ('Colombia', 'Liga DIMAYOR'),
    'deportes tolima': ('Colombia', 'Liga DIMAYOR'),
    'america de cali': ('Colombia', 'Liga DIMAYOR'),
    # Bolivia - Primera División
    'real potosi': ('Bolivia', 'Primera División'),
    'cdt real oruro': ('Bolivia', 'Primera División'),
    'real oruro': ('Bolivia', 'Primera División'),
    'club bolívar': ('Bolivia', 'Primera División'),
    'bolivar': ('Bolivia', 'Primera División'),
    'the strongest': ('Bolivia', 'Primera División'),
    'oriente petrolero': ('Bolivia', 'Primera División'),
    'wilstermann': ('Bolivia', 'Primera División'),
    'nacional potosi': ('Bolivia', 'Primera División'),
    'aurora': ('Bolivia', 'Primera División'),
    'always ready': ('Bolivia', 'Primera División'),
    # Portugal - extra
    'famalicao': ('Portugal', 'Primeira Liga'),
    'famalicão': ('Portugal', 'Primeira Liga'),
    'arouca': ('Portugal', 'Primeira Liga'),
    'casa pia': ('Portugal', 'Primeira Liga'),
    'gil vicente': ('Portugal', 'Primeira Liga'),
    'pacos de ferreira': ('Portugal', 'Primeira Liga'),
    'chaves': ('Portugal', 'Primeira Liga'),
    'moreirense': ('Portugal', 'Primeira Liga'),
    'vizela': ('Portugal', 'Primeira Liga'),
    'rio ave': ('Portugal', 'Primeira Liga'),
    # Japan
    'urawa': ('Japan', 'J1 League'),
    'urawa red diamonds': ('Japan', 'J1 League'),
    'kawasaki': ('Japan', 'J1 League'),
    'kawasaki frontale': ('Japan', 'J1 League'),
    'gamba osaka': ('Japan', 'J1 League'),
    'kashima antlers': ('Japan', 'J1 League'),
    'vissel kobe': ('Japan', 'J1 League'),
    'yokohama f marinos': ('Japan', 'J1 League'),
    'cerezo osaka': ('Japan', 'J1 League'),
    'nagoya grampus': ('Japan', 'J1 League'),
    # Austria - Bundesliga
    'red bull salzburg':  ('Austria', 'Bundesliga'),
    'rb salzburg':        ('Austria', 'Bundesliga'),
    'fc salzburg':        ('Austria', 'Bundesliga'),
    'salzburg':           ('Austria', 'Bundesliga'),
    'sturm graz':         ('Austria', 'Bundesliga'),
    'rapid vienna':       ('Austria', 'Bundesliga'),
    'rapid wien':         ('Austria', 'Bundesliga'),
    'austria vienna':     ('Austria', 'Bundesliga'),
    'austria wien':       ('Austria', 'Bundesliga'),
    'sk rapid':           ('Austria', 'Bundesliga'),
    'lask':               ('Austria', 'Bundesliga'),
    'wolfsberg':          ('Austria', 'Bundesliga'),
    'blau-weiss linz':    ('Austria', 'Bundesliga'),
    'wsb wolfsberg':      ('Austria', 'Bundesliga'),
    'rheindorf altach':   ('Austria', 'Bundesliga'),
    'sc rheindorf altach': ('Austria', 'Bundesliga'),
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

# Betfair competition name → (country, league)
# Keys are lowercased for case-insensitive lookup.
# Country code (ISO 3166) used to disambiguate identical competition names.
BETFAIR_COMPETITION_MAP = {
    # England
    'premier league':              ('England', 'Premier League'),
    'english premier league':      ('England', 'Premier League'),
    'championship':                ('England', 'Championship'),
    'league one':                  ('England', 'League One'),
    'league two':                  ('England', 'League Two'),
    'fa cup':                      ('England', 'FA Cup'),
    'efl cup':                     ('England', 'EFL Cup'),
    # Scotland
    'scottish premiership':        ('Scotland', 'Scottish Premiership'),
    'scottish championship':       ('Scotland', 'Scottish Championship'),
    # Spain
    'la liga':                     ('Spain', 'La Liga'),
    'segunda división':            ('Spain', 'Segunda'),
    'segunda division':            ('Spain', 'Segunda'),
    # Germany
    'bundesliga':                  ('Germany', 'Bundesliga'),
    '2. bundesliga':               ('Germany', '2. Bundesliga'),
    # Italy
    'serie a':                     ('Italy', 'Serie A'),     # may be overridden by country_code
    'serie b':                     ('Italy', 'Serie B'),
    # France
    'ligue 1':                     ('France', 'Ligue 1'),
    'ligue 2':                     ('France', 'Ligue 2'),
    # Turkey
    'süper lig':                   ('Turkey', 'Super Lig'),
    'super lig':                   ('Turkey', 'Super Lig'),
    # Netherlands
    'eredivisie':                  ('Netherlands', 'Eredivisie'),
    # Belgium
    'jupiler pro league':          ('Belgium', 'Pro League'),
    'belgian first division a':    ('Belgium', 'Pro League'),
    # Portugal
    'primeira liga':               ('Portugal', 'Primeira Liga'),
    'liga portugal':               ('Portugal', 'Primeira Liga'),
    # Greece
    'super league':                ('Greece', 'Super League'),
    'super league 1':              ('Greece', 'Super League'),
    # Romania
    'liga 1':                      ('Romania', 'Liga 1'),
    # Croatia
    'hnl':                         ('Croatia', 'HNL'),
    # Sweden
    'allsvenskan':                 ('Sweden', 'Allsvenskan'),
    'superettan':                  ('Sweden', 'Superettan'),
    # Norway
    'eliteserien':                 ('Norway', 'Eliteserien'),
    # Denmark
    'superliga':                   ('Denmark', 'Superliga'),
    'danish superliga':            ('Denmark', 'Superliga'),
    # Poland
    'ekstraklasa':                 ('Poland', 'Ekstraklasa'),
    # Czech Republic
    'czech first league':          ('Czech Republic', 'Czech Liga'),
    'fortuna liga':                ('Czech Republic', 'Czech Liga'),
    # Slovakia
    'super liga':                  ('Slovakia', 'Super Liga'),
    # Bulgaria
    'first professional league':   ('Bulgaria', 'First Professional League'),
    # Bosnia
    'premier league of bih':       ('Bosnia', 'Premier League'),
    # Georgia
    'erovnuli liga':               ('Georgia', 'Erovnuli Liga'),
    # USA
    'mls':                         ('USA', 'MLS'),
    'major league soccer':         ('USA', 'MLS'),
    # Brazil
    'brasileirao':                 ('Brazil', 'Brasileirao'),
    'campeonato brasileiro':       ('Brazil', 'Brasileirao'),
    # Argentina
    'primera división':            ('Argentina', 'Primera División'),
    'primera division':            ('Argentina', 'Primera División'),
    'liga profesional':            ('Argentina', 'Primera División'),
    # Uruguay
    'primera division uru':        ('Uruguay', 'Primera División'),
    # Japan
    'j1 league':                   ('Japan', 'J1 League'),
    'j-league':                    ('Japan', 'J1 League'),
    # Europe
    'uefa champions league':       ('Europe', 'Champions League'),
    'uefa europa league':          ('Europe', 'Europa League'),
    'uefa europa conference league': ('Europe', 'Conference League'),
    'concacaf champions cup':      ('CONCACAF', 'Champions Cup'),
    'concacaf champions league':   ('CONCACAF', 'Champions Cup'),
    # Colombia
    'categoría primera a':         ('Colombia', 'Liga DIMAYOR'),
    'categoria primera a':         ('Colombia', 'Liga DIMAYOR'),
    'liga betplay dimayor':        ('Colombia', 'Liga DIMAYOR'),
    'colombian primera a':         ('Colombia', 'Liga DIMAYOR'),
    # Bolivia
    'bolivian primera division':   ('Bolivia', 'Primera División'),
    'liga boliviana':              ('Bolivia', 'Primera División'),
    'division profesional':        ('Bolivia', 'Primera División'),
    # Mexico
    'liga mx':                     ('Mexico', 'Liga MX'),
    'liga bbva mx':                ('Mexico', 'Liga MX'),
    # Denmark second tier
    'danish 1st division':         ('Denmark', '1. Division'),
    'danish first division':       ('Denmark', '1. Division'),
    '1. division':                 ('Denmark', '1. Division'),
    # Austria
    'austrian football bundesliga': ('Austria', 'Bundesliga'),
    'austrian bundesliga':          ('Austria', 'Bundesliga'),
    'admiral bundesliga':           ('Austria', 'Bundesliga'),
    'öfb cup':                      ('Austria', 'ÖFB Cup'),
    'ofb cup':                      ('Austria', 'ÖFB Cup'),
    'austria segunda liga':         ('Austria', '2. Liga'),
    # South America — international cups
    'copa libertadores':            ('South America', 'Copa Libertadores'),
    'conmebol libertadores':        ('South America', 'Copa Libertadores'),
    'copa sudamericana':            ('South America', 'Copa Sudamericana'),
    'conmebol sudamericana':        ('South America', 'Copa Sudamericana'),
    'recopa sudamericana':          ('South America', 'Recopa Sudamericana'),
    # CONCACAF
    'concacaf gold cup':            ('CONCACAF', 'Gold Cup'),
    # Switzerland
    'super league switzerland':     ('Switzerland', 'Super League'),
    'swiss super league':           ('Switzerland', 'Super League'),
    'axpo super league':            ('Switzerland', 'Super League'),
    # Serbia
    'serbian superliga':            ('Serbia', 'SuperLiga'),
    'mozzart bet superliga':        ('Serbia', 'SuperLiga'),
    # Russia
    'russian premier league':       ('Russia', 'Premier League'),
    # Israel
    'israeli premier league':       ('Israel', 'Premier League'),
    'ligat ha\'al':                  ('Israel', 'Premier League'),
    # Finland
    'veikkausliiga':                ('Finland', 'Veikkausliiga'),
    # China
    'chinese super league':         ('China', 'Super League'),
    # South Korea
    'k league 1':                   ('South Korea', 'K League 1'),
    'k-league 1':                   ('South Korea', 'K League 1'),
    # Peru
    'liga 1 peru':                  ('Peru', 'Liga 1'),
    'liga 1 betsson':               ('Peru', 'Liga 1'),
    # Ecuador
    'liga pro':                     ('Ecuador', 'Liga Pro'),
    'liga pro ecuador':             ('Ecuador', 'Liga Pro'),
    # Chile
    'primera division chile':       ('Chile', 'Primera División'),
    'campeonato chile':             ('Chile', 'Primera División'),
    # Paraguay
    'division profesional paraguay': ('Paraguay', 'División Profesional'),
    'asociacion paraguaya':         ('Paraguay', 'División Profesional'),
    # Venezuela
    'primera division venezuela':   ('Venezuela', 'Primera División'),
}

# Country code override for ambiguous competition names (e.g. "Serie A" = Italy or Brazil)
BETFAIR_COUNTRY_CODE_MAP = {
    'GB-ENG': 'England',
    'GB-SCT': 'Scotland',
    'GB-WAL': 'Wales',
    'ES':     'Spain',
    'DE':     'Germany',
    'IT':     'Italy',
    'FR':     'France',
    'TR':     'Turkey',
    'NL':     'Netherlands',
    'BE':     'Belgium',
    'PT':     'Portugal',
    'GR':     'Greece',
    'RO':     'Romania',
    'HR':     'Croatia',
    'SE':     'Sweden',
    'NO':     'Norway',
    'DK':     'Denmark',
    'PL':     'Poland',
    'CZ':     'Czech Republic',
    'SK':     'Slovakia',
    'BG':     'Bulgaria',
    'BA':     'Bosnia',
    'GE':     'Georgia',
    'US':     'USA',
    'BR':     'Brazil',
    'AR':     'Argentina',
    'UY':     'Uruguay',
    'JP':     'Japan',
    'MX':     'Mexico',
    'BO':     'Bolivia',
    'CO':     'Colombia',
    'COL':    'Colombia',
    'PE':     'Peru',
    'EC':     'Ecuador',
    'CL':     'Chile',
    'VE':     'Venezuela',
    'US':     'USA',
}

# League rank within a country (lower = higher tier). Used to resolve cross-league matches.
_LEAGUE_RANK = {
    'Premier League': 1, 'Championship': 2, 'League One': 3, 'League Two': 4,
    'FA Cup': 1, 'EFL Cup': 1,
    'La Liga': 1, 'Segunda': 2,
    'Bundesliga': 1, '2. Bundesliga': 2,
    'Serie A': 1, 'Serie B': 2,
    'Ligue 1': 1, 'Ligue 2': 2,
    'Scottish Premiership': 1, 'Scottish Championship': 2,
    'Super Lig': 1,
    'Eredivisie': 1,
    'Pro League': 1,
    'Primeira Liga': 1,
    'Super League': 1,
    'Liga 1': 1,
    'HNL': 1,
    'Allsvenskan': 1, 'Superettan': 2,
    'Eliteserien': 1,
    'Superliga': 1,
    'Ekstraklasa': 1,
    'MLS': 1,
    'Brasileirao': 1,
    'Primera División': 1,
    'Champions League': 0, 'Europa League': 0, 'Conference League': 0, 'European': 0,
    'Liga MX': 1,
    'Primera División': 1,
    '1. Division': 2,
}

# Competition keywords for smart detection — searched in the raw match string (lowercase)
# Order matters: longer/more-specific entries should come first.
COMPETITION_KEYWORDS = [
    ('uefa europa conference league', 'Europe', 'Conference League'),
    ('europa conference league',      'Europe', 'Conference League'),
    ('conference league',             'Europe', 'Conference League'),
    ('uefa europa league',            'Europe', 'Europa League'),
    ('europa league',                 'Europe', 'Europa League'),
    ('uefa champions league',         'Europe', 'Champions League'),
    ('champions league',              'Europe', 'Champions League'),
    ('carabao cup',                   'England', 'EFL Cup'),
    ('efl cup',                       'England', 'EFL Cup'),
    ('league cup',                    'England', 'EFL Cup'),
    ('fa cup',                        'England', 'FA Cup'),
    ('community shield',              'England', 'Community Shield'),
    ('copa del rey',                  'Spain', 'Copa del Rey'),
    ('dfb-pokal',                     'Germany', 'DFB Pokal'),
    ('dfb pokal',                     'Germany', 'DFB Pokal'),
    ('coppa italia',                  'Italy', 'Coppa Italia'),
    ('coupe de france',               'France', 'Coupe de France'),
    ('european championship',         'International', 'European Championship'),
    ('nations league',                'International', 'Nations League'),
    ('world cup',                     'International', 'World Cup'),
]

# TheSportsDB league names → (country, league) for external API fallback
SPORTSDB_LEAGUE_MAP = {
    'english premier league':                ('England', 'Premier League'),
    'english football league championship':  ('England', 'Championship'),
    'english football league one':           ('England', 'League One'),
    'english football league two':           ('England', 'League Two'),
    'scottish premiership':                  ('Scotland', 'Scottish Premiership'),
    'spanish la liga':                       ('Spain', 'La Liga'),
    'spanish segunda division':              ('Spain', 'Segunda'),
    'german bundesliga':                     ('Germany', 'Bundesliga'),
    'german 2. bundesliga':                  ('Germany', '2. Bundesliga'),
    'italian serie a':                       ('Italy', 'Serie A'),
    'italian serie b':                       ('Italy', 'Serie B'),
    'french ligue 1':                        ('France', 'Ligue 1'),
    'french ligue 2':                        ('France', 'Ligue 2'),
    'dutch eredivisie':                      ('Netherlands', 'Eredivisie'),
    'portuguese primeira liga':              ('Portugal', 'Primeira Liga'),
    'belgian pro league':                    ('Belgium', 'Pro League'),
    'turkish super lig':                     ('Turkey', 'Super Lig'),
    'greek super league':                    ('Greece', 'Super League'),
    'swedish allsvenskan':                   ('Sweden', 'Allsvenskan'),
    'norwegian eliteserien':                 ('Norway', 'Eliteserien'),
    'danish superliga':                      ('Denmark', 'Superliga'),
    'polish ekstraklasa':                    ('Poland', 'Ekstraklasa'),
    'major league soccer':                   ('USA', 'MLS'),
    'mls':                                   ('USA', 'MLS'),
    'j1 league':                             ('Japan', 'J1 League'),
    'brasileirao serie a':                   ('Brazil', 'Brasileirao'),
    'argentine primera division':            ('Argentina', 'Primera División'),
    'uefa champions league':                 ('Europe', 'Champions League'),
    'uefa europa league':                    ('Europe', 'Europa League'),
    'uefa europa conference league':         ('Europe', 'Conference League'),
}

_SPORTSDB_CACHE = {}  # team name (lowercase) → (country, league) or None

# Horse racing tracks → country mapping (lowercase track name → display country)
HORSE_RACING_TRACK_COUNTRY = {
    # England
    'ascot': 'England', 'cheltenham': 'England', 'newmarket': 'England',
    'epsom': 'England', 'sandown': 'England', 'goodwood': 'England',
    'york': 'England', 'haydock': 'England', 'kempton': 'England',
    'lingfield': 'England', 'wolverhampton': 'England', 'chester': 'England',
    'newcastle': 'England', 'nottingham': 'England', 'leicester': 'England',
    'brighton': 'England', 'windsor': 'England', 'bath': 'England',
    'carlisle': 'England', 'catterick': 'England', 'exeter': 'England',
    'huntingdon': 'England', 'market rasen': 'England', 'plumpton': 'England',
    'pontefract': 'England', 'redcar': 'England', 'ripon': 'England',
    'salisbury': 'England', 'southwell': 'England', 'stratford': 'England',
    'taunton': 'England', 'thirsk': 'England', 'wetherby': 'England',
    'wincanton': 'England', 'worcester': 'England', 'yarmouth': 'England',
    'doncaster': 'England', 'newbury': 'England', 'beverley': 'England',
    'warwick': 'England', 'folkestone': 'England', 'hereford': 'England',
    'ludlow': 'England', 'bangor': 'England', 'uttoxeter': 'England',
    'fakenham': 'England', 'towcester': 'England', 'hexham': 'England',
    'sedgefield': 'England', 'kelso': 'Scotland',
    # Scotland
    'musselburgh': 'Scotland', 'perth': 'Scotland', 'ayr': 'Scotland',
    'hamilton': 'Scotland',
    # Wales
    'chepstow': 'Wales', 'ffos las': 'Wales',
    # Ireland
    'curragh': 'Ireland', 'leopardstown': 'Ireland', 'galway': 'Ireland',
    'punchestown': 'Ireland', 'fairyhouse': 'Ireland', 'navan': 'Ireland',
    'tipperary': 'Ireland', 'gowran': 'Ireland', 'listowel': 'Ireland',
    'dundalk': 'Ireland', 'naas': 'Ireland', 'limerick': 'Ireland',
    'roscommon': 'Ireland', 'sligo': 'Ireland', 'thurles': 'Ireland',
    'tralee': 'Ireland', 'down royal': 'Ireland', 'bellewstown': 'Ireland',
    'clonmel': 'Ireland', 'killarney': 'Ireland', 'ballinrobe': 'Ireland',
    'tramore': 'Ireland', 'kilbeggan': 'Ireland', 'laytown': 'Ireland',
    'cork': 'Ireland',
}

# Flat set for fast detection
HORSE_RACING_TRACKS = set(HORSE_RACING_TRACK_COUNTRY.keys())

# Football-specific bet type terms that rule out horse racing
_FOOTBALL_BET_TERMS = {
    'goals', 'btts', 'both teams', 'corner', 'card', 'yellow', 'clean sheet',
    'first scorer', 'anytime scorer', 'double chance', 'half time', 'asian',
    'over 0', 'over 1', 'over 2', 'over 3', 'over 4', 'over 5',
    'under 0', 'under 1', 'under 2', 'under 3', 'under 4', 'under 5',
}

def detect_sport(record):
    """Classify a bet as 'Horse Racing', 'Football', or None (uncertain).

    Returning None tells the caller to PRESERVE the existing sport label —
    important so that Betfair-sourced Golf/Tennis/Cricket records aren't
    silently overwritten as Football by the startup reenrich pass."""
    match   = (record.get('match')    or '').lower()
    bt      = (record.get('bet_type') or '').lower()
    league  = (record.get('league')   or '').lower()

    # Strong horse racing signal: "HH:MM Venue" time-prefix format
    if re.match(r'^\d{1,2}:\d{2}\s', match):
        return 'Horse Racing'

    # Strong football signal: "Team A v Team B" pattern
    if ' v ' in match or ' vs ' in match:
        return 'Football'

    # Strong football signal: football-specific bet type
    for term in _FOOTBALL_BET_TERMS:
        if term in bt:
            return 'Football'

    # Strong horse racing signal: known UK/Irish venue in match or league
    for track in HORSE_RACING_TRACKS:
        if track in match or track in league:
            return 'Horse Racing'

    # Generic 'win'/'each way' market is ambiguous (golf outright also uses
    # these), so we don't auto-assume Horse Racing — caller keeps existing label.
    return None


def get_country_league_betfair(competition_name, country_code, match):
    """Resolve country/league from Betfair competition metadata, falling back to team matching."""
    comp_key = (competition_name or '').lower().strip()
    if comp_key and comp_key in BETFAIR_COMPETITION_MAP:
        country, league = BETFAIR_COMPETITION_MAP[comp_key]
        # Disambiguate ambiguous leagues (e.g. "Serie A") using country_code
        if country_code and country_code in BETFAIR_COUNTRY_CODE_MAP:
            country = BETFAIR_COUNTRY_CODE_MAP[country_code]
        return country, league
    # Fall back to team-name matching
    return get_country_league(match)

def get_country_league(match):
    """Detect country and league from match name using team mapping.

    Logic order:
    1. Youth patterns (U18/U19/U21/U23) — checked before team matching so
       "Crewe U21 v QPR U21" isn't misclassified as Championship.
    2. Women's patterns.
    3. Collect ALL teams found in the match string.
    4. If teams from different countries → Europe/European (cross-country fixture).
    5. If teams from the same country but different leagues → pick highest-ranked league.
    """
    match_lower = match.lower().replace('�', '')

    # Youth detection first
    if re.search(r'\bu\s*18\b|\bu-18\b', match_lower):
        return 'Youth', 'U18'
    if re.search(r'\bu\s*19\b|\bu-19\b', match_lower):
        return 'Youth', 'U19'
    if re.search(r'\bu\s*21\b|\bu-21\b', match_lower):
        return 'Youth', 'U21'
    if re.search(r'\bu\s*23\b|\bu-23\b', match_lower):
        return 'Youth', 'U23'
    if '(w)' in match_lower:
        return "Women's", "Women's Football"

    # Collect all matching teams.
    # - Longest keys first so 'liverpool montevideo' is claimed before 'liverpool'.
    # - Word-boundary regex prevents 'braga' matching inside 'bragantino', 'lyn' inside 'lyngby', etc.
    # - Position tracking prevents shorter keys from claiming character ranges already consumed.
    found = []
    used_ranges = []  # list of (start, end) character ranges already claimed

    for team in sorted(TEAM_MAP.keys(), key=len, reverse=True):
        try:
            # Only anchor with \b where the team name starts/ends on a word character.
            # e.g. 'racing club (uru)' ends with ')' so no trailing \b.
            lb = r'\b' if team[0].isalnum() or team[0] == '_' else r''
            rb = r'\b' if team[-1].isalnum() or team[-1] == '_' else r''
            m = re.search(lb + re.escape(team) + rb, match_lower)
        except re.error:
            idx = match_lower.find(team)
            if idx < 0:
                continue
            ms, me = idx, idx + len(team)
            if any(ms < r_end and me > r_start for r_start, r_end in used_ranges):
                continue
            entry = TEAM_MAP[team]
            if entry not in found:
                found.append(entry)
            used_ranges.append((ms, me))
            continue
        if not m:
            continue
        ms, me = m.start(), m.end()
        # Skip if this range overlaps an already-claimed range
        if any(ms < r_end and me > r_start for r_start, r_end in used_ranges):
            continue
        entry = TEAM_MAP[team]
        if entry not in found:
            found.append(entry)
        used_ranges.append((ms, me))

    if not found:
        return 'Other', 'Other'

    # Cross-country fixture
    countries = set(c for c, _ in found)
    if len(countries) > 1:
        # CONCACAF: USA/Canada/Mexico vs each other → CONCACAF Champions Cup
        _CONCACAF = {'USA', 'Mexico', 'Canada'}
        if countries.issubset(_CONCACAF):
            return 'CONCACAF', 'Champions Cup'

        # All-South-America cross-country fixture → Copa competition
        _SOUTH_AMERICA = {'Brazil', 'Argentina', 'Colombia', 'Uruguay', 'Bolivia',
                          'Peru', 'Ecuador', 'Chile', 'Venezuela', 'Paraguay'}
        if countries.issubset(_SOUTH_AMERICA):
            return 'South America', 'Copa'

        # Champions League clubs (recent regular CL participants)
        # NOTE: use word-boundary matching to avoid 'inter' matching 'internacional' etc.
        _CL_CLUBS = {
            'liverpool', 'manchester city', 'arsenal', 'chelsea', 'newcastle', 'aston villa',
            'real madrid', 'barcelona', 'atletico madrid',
            'bayern munich', 'bayern münchen', 'borussia dortmund', 'rb leipzig', 'bayer leverkusen',
            'juventus', 'inter milan', 'ac milan', 'napoli', 'atalanta',
            'paris st-g', 'psg', 'paris saint-germain', 'paris sg', 'monaco',
            'porto', 'benfica', 'sporting cp',
            'ajax', 'psv eindhoven', 'feyenoord',
            'celtic', 'shakhtar', 'red star',
            'galatasaray',
            'nottm forest', 'nottingham forest',
        }
        # Europa League tier clubs
        _EL_CLUBS = {
            'sc braga', 'braga',
            'real betis', 'sevilla', 'villarreal',
            'lille', 'marseille', 'lyon',
            'sc freiburg', 'freiburg',
            'roma', 'lazio',
            'fenerbahçe', 'fenerbahce',
            'fcsb', 'slavia prague', 'viktoria plzen',
        }
        # Conference League tier clubs
        _ECL_CLUBS = {
            'crystal palace', 'west ham',
            'fiorentina',
            'eintracht frankfurt',
            'fc midtjylland', 'midtjylland',
            'zrinjski', 'ludogorets',
            'paok', 'utrecht', 'genk',
            'nice',
            'rangers',
        }

        def _wb(name):
            lb = r'\b' if name[0].isalnum() else ''
            rb = r'\b' if name[-1].isalnum() else ''
            return bool(re.search(lb + re.escape(name) + rb, match_lower))

        cl_hits  = sum(1 for c in _CL_CLUBS  if _wb(c))
        el_hits  = sum(1 for e in _EL_CLUBS   if _wb(e))
        ecl_hits = sum(1 for e in _ECL_CLUBS  if _wb(e))

        if cl_hits >= 2:
            return 'Europe', 'Champions League'
        if cl_hits == 1 and el_hits == 0 and ecl_hits == 0:
            return 'Europe', 'Champions League'
        if el_hits >= 1 and cl_hits == 0:
            return 'Europe', 'Europa League'
        if ecl_hits >= 1 and cl_hits == 0 and el_hits == 0:
            return 'Europe', 'Conference League'

        return 'Europe', 'European'

    # Single country — pick highest-ranked league if teams disagree
    country = found[0][0]
    leagues = list(dict.fromkeys(l for _, l in found))
    if len(leagues) == 1:
        return country, leagues[0]
    return country, min(leagues, key=lambda l: _LEAGUE_RANK.get(l, 99))

def get_country_league_pdf(league_text, match):
    """Detect country/league using explicit PDF league text first, then team mapping."""
    for league_name, (country, league) in sorted(PDF_LEAGUE_MAP.items(), key=lambda x: -len(x[0])):
        if league_name.lower() in league_text.lower():
            return country, league
    return get_country_league(match)

def _fuzzy_team_lookup(team_text, threshold=0.82):
    """Fuzzy-match a team name against TEAM_MAP using difflib. Returns (entry, ratio) or (None, 0)."""
    team_lower = team_text.lower().strip()
    if team_lower in TEAM_MAP:
        return TEAM_MAP[team_lower], 1.0
    matches = difflib.get_close_matches(team_lower, TEAM_MAP.keys(), n=1, cutoff=threshold)
    if matches:
        ratio = difflib.SequenceMatcher(None, team_lower, matches[0]).ratio()
        return TEAM_MAP[matches[0]], ratio
    return None, 0.0

def _extract_teams_from_match(match):
    """Split 'Team A v Team B' into ['Team A', 'Team B'], stripping parenthetical noise."""
    clean = re.sub(r'\([^)]*\)', '', match).strip()
    parts = re.split(r'\s+v(?:s\.?|\.?)\s+|\s+@\s+', clean, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()][:2]

def _lookup_team_sportsdb(team_name):
    """Query TheSportsDB API for team league info. Results cached in _SPORTSDB_CACHE."""
    import requests as req
    key = team_name.lower().strip()
    if key in _SPORTSDB_CACHE:
        return _SPORTSDB_CACHE[key]
    try:
        url = ('https://www.thesportsdb.com/api/v1/json/3/searchteams.php'
               f'?t={urllib.parse.quote(team_name)}')
        resp = req.get(url, timeout=4)
        if resp.status_code == 200:
            teams = resp.json().get('teams') or []
            if teams:
                league_raw = (teams[0].get('strLeague') or '').lower().strip()
                if league_raw in SPORTSDB_LEAGUE_MAP:
                    result = SPORTSDB_LEAGUE_MAP[league_raw]
                    _SPORTSDB_CACHE[key] = result
                    return result
                for map_key, val in SPORTSDB_LEAGUE_MAP.items():
                    if map_key in league_raw or league_raw in map_key:
                        _SPORTSDB_CACHE[key] = val
                        return val
    except Exception:
        pass
    _SPORTSDB_CACHE[key] = None
    return None

# ---- TheSportsDB match-result (score) lookup --------------------------------
# Betfair purges settled markets within hours, so scores are sourced from
# TheSportsDB by match name + date. Free key '3' only covers major leagues;
# a premium (Patreon) key set in Settings unlocks full coverage.
_SPORTSDB_DAY_CACHE = {}   # (date_day, api_key) -> list of soccer events that day

def _norm_team(name):
    """Normalise a team name for fuzzy comparison (strip accents/suffixes/punct)."""
    import unicodedata
    s = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode()
    s = s.lower()
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    # Drop common club tokens that vary between sources
    drop = {'fc', 'cf', 'ec', 'sc', 'afc', 'cd', 'ca', 'ac', 'club', 'de', 'do',
            'da', 'the', 'united', 'utd', 'city'}
    toks = [t for t in s.split() if t and t not in drop]
    return ' '.join(toks) if toks else s.strip()

def _split_match(match):
    """Split 'Team A v Team B' (or 'vs') into (home, away); None if not parseable."""
    parts = re.split(r'\s+v(?:s\.?)?\s+', match or '', flags=re.I)
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        return parts[0].strip(), parts[1].strip()
    return None, None

def _sportsdb_events_for_date(date_day, api_key):
    """All soccer events on a date (cached per date+key). One API call per date."""
    ck = (date_day, api_key)
    if ck in _SPORTSDB_DAY_CACHE:
        return _SPORTSDB_DAY_CACHE[ck]
    import requests as req
    events = []
    try:
        url = (f'https://www.thesportsdb.com/api/v1/json/{api_key}/eventsday.php'
               f'?d={date_day}&s=Soccer')
        resp = req.get(url, timeout=8)
        if resp.status_code == 200:
            events = (resp.json() or {}).get('events') or []
    except Exception as e:
        print(f"TheSportsDB eventsday failed for {date_day}: {e}")
        events = []
    _SPORTSDB_DAY_CACHE[ck] = events
    return events

def _lookup_score_sportsdb(match, date_day, api_key):
    """Return the final score as 'H-A' oriented to our match order, or None."""
    from difflib import SequenceMatcher
    home, away = _split_match(match)
    if not home or not away:
        return None
    events = _sportsdb_events_for_date(date_day, api_key)
    if not events:
        return None
    nh, na = _norm_team(home), _norm_team(away)
    best_ev, best_sc, best_swapped = None, 0.0, False
    for ev in events:
        eh = _norm_team(ev.get('strHomeTeam') or '')
        ea = _norm_team(ev.get('strAwayTeam') or '')
        if not eh or not ea:
            continue
        direct  = (SequenceMatcher(None, nh, eh).ratio() + SequenceMatcher(None, na, ea).ratio()) / 2
        swapped = (SequenceMatcher(None, nh, ea).ratio() + SequenceMatcher(None, na, eh).ratio()) / 2
        sc = max(direct, swapped)
        if sc > best_sc:
            best_sc, best_ev, best_swapped = sc, ev, swapped > direct
    if not best_ev or best_sc < 0.7:
        return None
    hs, as_ = best_ev.get('intHomeScore'), best_ev.get('intAwayScore')
    if hs is None or as_ is None or str(hs).strip() == '' or str(as_).strip() == '':
        return None
    # Orient the score to OUR match order (our 'home' first).
    return f"{as_}-{hs}" if best_swapped else f"{hs}-{as_}"

def auto_detect_league_smart(match, source=None):
    """Multi-method league detection. Returns (country, league, method, confidence).

    Methods in priority order:
    1. Exact team map  — get_country_league()
    2. Competition keyword scan of the match string
    3. Fuzzy team-name matching via difflib
    4. TheSportsDB external API (network, cached)
    """
    match = match or ''

    # 1 — exact team map
    country, league = get_country_league(match)
    if country != 'Other':
        return country, league, 'team_map', 'high'

    # 2 — competition keywords
    match_lower = match.lower()
    for keyword, kw_country, kw_league in COMPETITION_KEYWORDS:
        if keyword in match_lower:
            return kw_country, kw_league, 'keyword', 'high'

    # 3 — fuzzy team matching
    teams = _extract_teams_from_match(match)
    fuzzy_hits = []
    for team_text in teams:
        entry, ratio = _fuzzy_team_lookup(team_text)
        if entry:
            fuzzy_hits.append((entry, ratio))

    if fuzzy_hits:
        fuzzy_hits.sort(key=lambda x: -x[1])
        entries = [e for e, _ in fuzzy_hits]
        avg_ratio = sum(r for _, r in fuzzy_hits) / len(fuzzy_hits)
        confidence = 'high' if avg_ratio >= 0.90 else 'medium'
        countries = set(c for c, _ in entries)
        if len(countries) > 1:
            return 'Europe', 'European', 'fuzzy_team', confidence
        c = entries[0][0]
        leagues = list(dict.fromkeys(l for _, l in entries))
        if len(leagues) == 1:
            return c, leagues[0], 'fuzzy_team', confidence
        return c, min(leagues, key=lambda l: _LEAGUE_RANK.get(l, 99)), 'fuzzy_team', confidence

    # 4 — TheSportsDB API
    for team_text in teams:
        result = _lookup_team_sportsdb(team_text)
        if result:
            return result[0], result[1], 'external_api', 'medium'

    return 'Other', 'Other', 'none', 'low'

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
    for col, definition in [('source', 'TEXT DEFAULT "csv"'), ('odds', 'REAL'), ('sport', 'TEXT'), ('bet_category', 'TEXT'), ('bf_competition', 'TEXT'), ('bf_country_code', 'TEXT'), ('bf_raw_data', 'TEXT'), ('correct_score', 'TEXT'), ('correct_score_status', 'TEXT')]:
        try:
            c.execute(f'ALTER TABLE bets ADD COLUMN {col} {definition}')
        except Exception:
            pass
    # Tombstone table: prevents manually-deleted bets from being re-imported
    c.execute('''CREATE TABLE IF NOT EXISTS deleted_bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        norm_match TEXT,
        norm_bet_type TEXT,
        stake REAL,
        date_day TEXT,
        deleted_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    # User-defined team→country/league mappings (merged into TEAM_MAP at startup)
    c.execute('''CREATE TABLE IF NOT EXISTS custom_team_map (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_name TEXT UNIQUE,
        country TEXT,
        league TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    # Strategy bets table — isolated from main `bets` table. Holds in-play trigger
    # rows imported from Betsoccer xlsx files. Full row payload kept as JSON so
    # we don't have to migrate every time a column is added.
    c.execute('''CREATE TABLE IF NOT EXISTS strategy_bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy TEXT,
        source_file TEXT,
        alert_date TEXT,
        timer INTEGER,
        strike INTEGER,
        region TEXT,
        league TEXT,
        home_team TEXT,
        away_team TEXT,
        data_json TEXT,
        imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(strategy, alert_date, home_team, away_team, timer)
    )''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def load_custom_team_map():
    """Load user-defined team mappings from DB and merge into TEAM_MAP."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT team_name, country, league FROM custom_team_map')
    for row in c.fetchall():
        TEAM_MAP[row['team_name'].lower().strip()] = (row['country'], row['league'])
    conn.close()

def db_tombstone_ids(ids):
    """Record normalised fingerprints of bets being deleted so they can't be re-imported."""
    conn = get_db()
    c = conn.cursor()
    placeholders = ','.join('?' for _ in ids)
    c.execute(f'SELECT date, match, bet_type, stake FROM bets WHERE id IN ({placeholders})', ids)
    for row in c.fetchall():
        c.execute(
            'INSERT INTO deleted_bets (norm_match, norm_bet_type, stake, date_day) VALUES (?,?,?,?)',
            (normalize_match_name(str(row[1] or '')),
             normalize_bet_type(str(row[2] or '')),
             float(row[3] or 0),
             str(row[0] or '')[:10])
        )
    conn.commit()
    conn.close()

def _is_tombstoned(conn, norm_match, norm_bt, stake_val, date_day):
    """Return True if this bet was previously deleted by the user."""
    try:
        dt = datetime.strptime(date_day, '%Y-%m-%d')
        date_from = (dt - timedelta(days=1)).strftime('%Y-%m-%d')
        date_to   = (dt + timedelta(days=1)).strftime('%Y-%m-%d')
    except Exception:
        date_from = date_to = date_day
    c = conn.cursor()
    c.execute(
        'SELECT 1 FROM deleted_bets WHERE norm_match=? AND norm_bet_type=? '
        'AND ABS(stake-?)<=0.01 AND date_day>=? AND date_day<=? LIMIT 1',
        (norm_match, norm_bt, stake_val, date_from, date_to)
    )
    return c.fetchone() is not None

def db_insert_bet(bet, source='csv'):
    """Insert bet if not a duplicate. Returns True if inserted.

    Betfair takes precedence over CSV/PDF: if a Betfair record matches an
    existing CSV/PDF record it replaces it. CSV/PDF records are skipped when
    any matching record (any source) already exists.

    Duplicate = same normalised match name, normalised bet type, and stake,
    with a date within ±1 calendar day.
    """
    conn = get_db()
    c = conn.cursor()
    date_day = str(bet.get('date', ''))[:10]
    norm_match = normalize_match_name(bet.get('match', ''))
    norm_bt = normalize_bet_type(bet.get('bet_type', ''))
    stake_val = float(bet.get('stake') or 0)

    try:
        dt = datetime.strptime(date_day, '%Y-%m-%d')
        date_from = (dt - timedelta(days=1)).strftime('%Y-%m-%d')
        date_to = (dt + timedelta(days=1)).strftime('%Y-%m-%d')
    except Exception:
        date_from = date_to = date_day

    # Block re-import of anything the user explicitly deleted
    if _is_tombstoned(conn, norm_match, norm_bt, stake_val, date_day):
        conn.close()
        return False

    c.execute(
        "SELECT id, date, match, bet_type, stake, source, bet_category, bf_raw_data FROM bets "
        "WHERE substr(date,1,10) >= ? AND substr(date,1,10) <= ?",
        (date_from, date_to)
    )
    csv_ids_to_replace = []
    has_betfair_match = False
    matching_betfair_id = None
    new_cat = (bet.get('bet_category') or '').strip()

    # When the new bet is Betfair, extract its bet_id so we can distinguish
    # two genuinely separate orders ("doubled up") from a true re-import.
    new_bet_id = ''
    if source == 'betfair':
        try:
            new_bet_id = str(json.loads(bet.get('bf_raw_data') or '{}').get('bet_id', '') or '').strip()
        except Exception:
            new_bet_id = ''

    for row in c.fetchall():
        e_id, e_date, e_match, e_bt, e_stake, e_source, e_bet_cat, e_raw = row
        if not (normalize_match_name(str(e_match or '')) == norm_match
                and normalize_bet_type(str(e_bt or '')) == norm_bt
                and abs(float(e_stake or 0) - stake_val) < 0.01
                and _dates_within_one_day(str(e_date or ''), date_day)):
            continue
        # Win and Place bets for the same horse are distinct — don't treat as duplicates
        if new_cat and (e_bet_cat or '').strip() and new_cat != (e_bet_cat or '').strip():
            continue
        if e_source == 'betfair':
            # Two Betfair orders with the same match/stake but different bet_id
            # are genuinely separate placements (doubled-up bets), not duplicates.
            if source == 'betfair' and new_bet_id:
                try:
                    existing_bet_id = str(json.loads(e_raw or '{}').get('bet_id', '') or '').strip()
                except Exception:
                    existing_bet_id = ''
                if existing_bet_id and existing_bet_id != new_bet_id:
                    continue   # same selection, different placement — keep both
            has_betfair_match = True
            matching_betfair_id = e_id
        else:
            csv_ids_to_replace.append(e_id)

    if source == 'betfair':
        if has_betfair_match:
            # Backfill bet_category if the existing record has it as NULL
            if matching_betfair_id and bet.get('bet_category'):
                c.execute(
                    "UPDATE bets SET bet_category = ? WHERE id = ? AND bet_category IS NULL",
                    (bet['bet_category'], matching_betfair_id)
                )
                conn.commit()
            conn.close()
            return False
        # Replace any matching CSV/PDF records with this Betfair record
        if csv_ids_to_replace:
            placeholders = ','.join('?' for _ in csv_ids_to_replace)
            c.execute(f'DELETE FROM bets WHERE id IN ({placeholders})', csv_ids_to_replace)
    else:
        # CSV/PDF: skip if any matching record exists (betfair or same source)
        if has_betfair_match or csv_ids_to_replace:
            conn.close()
            return False

    odds = bet.get('odds') or calc_odds(bet.get('pnl', 0), bet.get('stake', 0), bet.get('bet_type', ''))
    sport = bet.get('sport') or detect_sport(bet)
    c.execute(
        '''INSERT INTO bets (date, match, bet_type, market, stake, matched, status, pnl,
           country, league, source, odds, sport, bet_category, bf_competition, bf_country_code, bf_raw_data)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (bet.get('date', ''), bet.get('match', ''), bet.get('bet_type', ''),
         bet.get('market', ''), bet.get('stake', 0), bet.get('matched', 0),
         bet.get('status', ''), bet.get('pnl', 0),
         bet.get('country', ''), bet.get('league', ''), source, odds, sport,
         bet.get('bet_category') or None, bet.get('bf_competition') or None,
         bet.get('bf_country_code') or None, bet.get('bf_raw_data') or None)
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
    keys = ['id', 'date', 'match', 'bet_type', 'market', 'stake', 'matched', 'status', 'pnl', 'country', 'league', 'source', 'odds', 'sport', 'bet_category', 'bf_competition', 'bf_country_code', 'bf_raw_data', 'correct_score', 'correct_score_status']
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
    """Remove duplicates, preferring Betfair records over CSV/PDF.

    Within each duplicate group: keep the Betfair record if one exists,
    otherwise keep the earliest (lowest id). Betfair records are processed
    first so they anchor the kept set before CSV/PDF records are evaluated.
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, date, match, bet_type, stake, source FROM bets ORDER BY id ASC')
    rows = c.fetchall()

    # Process betfair rows first, then csv/pdf — ensures betfair always wins
    betfair_rows = [r for r in rows if r[5] == 'betfair']
    other_rows   = [r for r in rows if r[5] != 'betfair']
    ordered = betfair_rows + other_rows

    kept = []   # (id, date_str, norm_match, norm_bt, stake)
    delete_ids = []

    for rid, date, match, bet_type, stake, _ in ordered:
        date_str = str(date or '')[:10]
        norm_match = normalize_match_name(str(match or ''))
        norm_bt = normalize_bet_type(str(bet_type or ''))
        stake_val = float(stake or 0)

        is_dupe = any(
            k_nm == norm_match
            and k_nb == norm_bt
            and abs(k_st - stake_val) < 0.01
            and _dates_within_one_day(k_date, date_str)
            for _, k_date, k_nm, k_nb, k_st in kept
        )

        if is_dupe:
            delete_ids.append(rid)
        else:
            kept.append((rid, date_str, norm_match, norm_bt, stake_val))

    if delete_ids:
        placeholders = ','.join('?' for _ in delete_ids)
        c.execute(f'DELETE FROM bets WHERE id IN ({placeholders})', delete_ids)

    conn.commit()
    conn.close()
    return len(delete_ids)

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
            bet_type_val = str(row.get('Bet Type', ''))
            if re.match(r'^\d{2}:\d{2}', match):
                bet_type_val = bet_type_val.replace("'", "")
            bet = {
                'date': placed,
                'match': match,
                'bet_type': bet_type_val,
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
    """Normalize bet type: strip 'Back' prefix and unify Over/Under variants by line."""
    bt = (bt or '').strip()
    if bt.lower().startswith('back '):
        bt = bt[5:]
    m = re.match(r'^(over|under)\s+([\d.]+)\s+goals?$', bt, re.IGNORECASE)
    if m:
        return f"Over/Under {m.group(2)} Goals"
    return bt

def normalize_strategy_type(bt):
    """Classify a record into a strategy label for analysis filtering."""
    raw = (bt or '').strip().lower()
    norm = normalize_bet_type(raw).lower()
    if 'over/under 1.5 goals' == norm or ('over' in raw and '1.5' in raw):
        return 'Over 1.5'
    if 'draw' in raw and 'over' not in raw and 'under' not in raw:
        return 'Draw'
    if norm == 'draw' or norm == 'the draw':
        return 'Draw'
    return None

def normalize_match_name(match):
    """Normalize match name for duplicate comparison: lowercase, unify 'vs' → 'v'."""
    m = (match or '').lower().strip()
    m = re.sub(r'\s+vs\.?\s+', ' v ', m)
    m = re.sub(r'\s+', ' ', m)
    return m

def _dates_within_one_day(d1_str, d2_str):
    """Return True if two YYYY-MM-DD strings are within 1 calendar day of each other."""
    try:
        d1 = datetime.strptime(d1_str[:10], '%Y-%m-%d')
        d2 = datetime.strptime(d2_str[:10], '%Y-%m-%d')
        return abs((d1 - d2).days) <= 1
    except Exception:
        return d1_str[:10] == d2_str[:10]

def extract_markets(records):
    """Return sorted list of unique bet types (normalized) from records."""
    seen = set()
    for r in records:
        bt = normalize_bet_type(r.get('bet_type') or '')
        if bt and bt.lower() not in ('', 'unknown', 'n/a', 'other'):
            seen.add(bt)
    return sorted(seen)

def reenrich_leagues(force_all=False):
    """Re-map country/league for existing DB records.

    force_all=False (default): only fix records currently classified as Other/Unknown.
    force_all=True: re-classify ALL non-Betfair records so improved logic is applied to
                    previously mis-classified CSV/PDF records (e.g. cross-country fixtures,
                    wrong English league tier, U21 matches).
    """
    conn = get_db()
    c = conn.cursor()
    if force_all:
        c.execute(
            "SELECT id, match, country, source, bf_competition FROM bets "
            "WHERE sport != 'Horse Racing' OR sport IS NULL"
        )
    else:
        c.execute(
            "SELECT id, match, country, source, bf_competition FROM bets "
            "WHERE (sport != 'Horse Racing' OR sport IS NULL) "
            "AND (country IN ('Other','Unknown') "
            "OR league IN ('Other','Unknown') OR country IS NULL OR league IS NULL)"
        )
    rows = c.fetchall()
    updated = 0
    for row_id, match, current_country, source, bf_comp in rows:
        match = match or ''
        # Skip HR records that slipped through (sport NULL but match has time prefix)
        if re.match(r'^\d{1,2}:\d{2}\s', match):
            continue
        # Betfair records: use stored competition name if available (most reliable)
        if source == 'betfair' and bf_comp:
            country, league = get_country_league_betfair(bf_comp, '', match)
        else:
            country, league = get_country_league(match)
        if force_all:
            # Never downgrade a specific classification to Other/Other.
            # For Betfair records this preserves competition-sourced leagues
            # while still allowing cross-country/youth corrections.
            if country == 'Other' and (current_country or '') not in ('Other', 'Unknown', '', None):
                continue
        else:
            if country == 'Other' and league == 'Other':
                continue
        c.execute("UPDATE bets SET country=?, league=? WHERE id=?", (country, league, row_id))
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

    # --- Source filter ---
    selected_sources = config.get('selected_sources') or []
    if selected_sources:
        records = [r for r in records if (r.get('source') or 'csv') in selected_sources]

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

    selected_strategy_types = config.get('selected_strategy_types') or []
    if selected_strategy_types:
        records = [r for r in records
                   if normalize_strategy_type(r.get('bet_type') or '') in selected_strategy_types]

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
        elif strategy == 'compound_then_flat':
            flat_cap = float(config.get('flat_cap_stake', 100))
            comp_stake = round(current_bank * (stake_pct / 100), 2)
            day_stake = flat_cap if comp_stake >= flat_cap else comp_stake
            stake_per_bet_display = day_stake
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


def _analysis_member(record, pnl, odds=None):
    """Build a per-bet detail row for expandable analytics tables."""
    if odds is None:
        odds = float(record.get('odds') or 0)
    return {
        'date': str(record.get('date', ''))[:10],
        'match': record.get('match', '') or '',
        'league': f"{record.get('country', 'Other')} - {record.get('league', 'Other')}",
        'bet_type': record.get('bet_type', '') or '',
        'odds': round(odds, 2) if odds else 0,
        'pnl': round(pnl, 2),
        'result': 'WON' if pnl > 0 else ('LOST' if pnl < 0 else 'VOID'),
        'correct_score': record.get('correct_score') or '',
        'correct_score_status': record.get('correct_score_status') or '',
    }


def run_real_analysis(records, config):
    """Analyse bets using actual pnl/stake from the database — no staking simulation."""
    records = _apply_analysis_filters(records, config)
    commission = float(config.get('commission', 2.0)) / 100.0

    results = {
        'total_bets': 0, 'won': 0, 'lost': 0, 'void': 0,
        'total_stake': 0.0, 'total_pnl': 0.0,
        'roi': 0.0, 'win_rate': 0.0,
        'daily_results': [], 'weekly_results': [], 'league_breakdown': [],
    }

    from collections import defaultdict
    date_groups = defaultdict(list)
    for record in sorted(records, key=lambda r: str(r.get('date', ''))):
        status = str(record.get('status', '')).strip()
        if status not in ('Settled', 'WON', 'LOST'):
            continue
        date_key = str(record.get('date', ''))[:10]
        date_groups[date_key].append(record)

    daily_summary = {}
    processed_bets = []

    for date_key in sorted(date_groups.keys()):
        day_bets = day_won = day_lost = 0
        day_pnl = day_staked = 0.0
        day_members = []

        for record in date_groups[date_key]:
            raw_pnl = float(record.get('pnl', 0) or 0)
            pnl = round(raw_pnl * (1.0 - commission), 2) if raw_pnl > 0 else raw_pnl
            stake = float(record.get('stake', 0) or 0)

            results['total_bets'] += 1
            results['total_stake'] += stake
            results['total_pnl'] += pnl
            day_bets += 1
            day_staked += stake
            day_pnl += pnl

            if pnl > 0:
                results['won'] += 1
                day_won += 1
            elif pnl < 0:
                results['lost'] += 1
                day_lost += 1
            else:
                results['void'] += 1

            processed_bets.append({**record, 'actual_pnl': pnl})
            day_members.append(_analysis_member(record, pnl))

        day_win_rate = round((day_won / day_bets) * 100, 1) if day_bets > 0 else 0
        daily_summary[date_key] = {
            'bets': day_bets, 'won': day_won, 'lost': day_lost,
            'win_rate': day_win_rate,
            'pnl': round(day_pnl, 2),
            'staked': round(day_staked, 2),
            'members': sorted(day_members, key=lambda m: (-m['pnl'])),
        }

    results['total_pnl'] = round(results['total_pnl'], 2)
    results['total_stake'] = round(results['total_stake'], 2)
    if results['total_stake'] > 0:
        results['roi'] = round((results['total_pnl'] / results['total_stake']) * 100, 2)
    if results['total_bets'] > 0:
        results['win_rate'] = round((results['won'] / results['total_bets']) * 100, 1)

    results['daily_results'] = [{'date': k, **v} for k, v in sorted(daily_summary.items())]

    weekly_summary = {}
    for date_key, day in sorted(daily_summary.items()):
        try:
            dt = datetime.strptime(date_key, '%Y-%m-%d')
            wk = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
            if wk not in weekly_summary:
                weekly_summary[wk] = {'bets': 0, 'won': 0, 'lost': 0, 'pnl': 0.0, 'staked': 0.0, 'members': []}
            weekly_summary[wk]['bets'] += day['bets']
            weekly_summary[wk]['won'] += day['won']
            weekly_summary[wk]['lost'] += day['lost']
            weekly_summary[wk]['pnl'] = round(weekly_summary[wk]['pnl'] + day['pnl'], 2)
            weekly_summary[wk]['staked'] += day['staked']
            weekly_summary[wk]['members'].extend(day.get('members', []))
        except Exception:
            pass
    for wk_data in weekly_summary.values():
        wk_data['win_rate'] = round((wk_data['won'] / wk_data['bets']) * 100, 1) if wk_data['bets'] > 0 else 0
        wk_data['members'] = sorted(wk_data['members'], key=lambda m: (m['date'], -m['pnl']), reverse=True)
    results['weekly_results'] = [{'week': k, **v} for k, v in sorted(weekly_summary.items())]
    # Average weekly Win% (simple mean across weeks that have bets).
    _wk_rates = [w['win_rate'] for w in weekly_summary.values() if w['bets'] > 0]
    results['weekly_avg_win_rate'] = round(sum(_wk_rates) / len(_wk_rates), 1) if _wk_rates else 0.0

    league_summary = {}
    for bet in processed_bets:
        key = f"{bet.get('country', 'Other')} - {bet.get('league', 'Other')}"
        if key not in league_summary:
            league_summary[key] = {'bets': 0, 'won': 0, 'lost': 0, 'pnl': 0.0, 'stake': 0.0}
        bp = bet['actual_pnl']
        league_summary[key]['bets'] += 1
        league_summary[key]['pnl'] = round(league_summary[key]['pnl'] + bp, 2)
        league_summary[key]['stake'] += float(bet.get('stake', 0) or 0)
        if bp > 0:
            league_summary[key]['won'] += 1
        elif bp < 0:
            league_summary[key]['lost'] += 1
    for v in league_summary.values():
        v['win_rate'] = round((v['won'] / v['bets']) * 100, 1) if v['bets'] > 0 else 0
        v['roi'] = round((v['pnl'] / v['stake']) * 100, 2) if v['stake'] > 0 else 0
    results['league_breakdown'] = [
        {'league': k, **v} for k, v in sorted(league_summary.items(), key=lambda x: -x[1]['bets'])
    ]
    return results

# ==================== ROUTES ====================

def _split_records_by_sport(records):
    football = [r for r in records if r.get('sport') != 'Horse Racing']
    horses   = [r for r in records if r.get('sport') == 'Horse Racing']
    return football, horses


@app.route('/')
def index():
    records = data_store.get('data') or []
    football_records, hr_records = _split_records_by_sport(records)

    dates = sorted(str(r.get('date', ''))[:10] for r in records if r.get('date'))
    dates = [d for d in dates if d]

    hr_dates = sorted(str(r.get('date', ''))[:10] for r in hr_records if r.get('date'))
    hr_dates = [d for d in hr_dates if d]

    return render_template('index.html',
                           config=data_store['config'],
                           leagues=extract_leagues(football_records),
                           markets=extract_markets(football_records),
                           hr_tracks=extract_leagues(hr_records),
                           hr_markets=extract_markets(hr_records),
                           record_count=len(records),
                           date_min=dates[0] if dates else '',
                           date_max=dates[-1] if dates else '',
                           hr_date_min=hr_dates[0] if hr_dates else '',
                           hr_date_max=hr_dates[-1] if hr_dates else '')

@app.route('/data')
def data_page():
    records = data_store.get('data') or []
    return render_template('data.html', records=records, commission=data_store['config'].get('commission', 2.0))

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

@app.route('/analytics-real')
def analytics_real_page():
    records = data_store.get('data') or []
    football_records = [r for r in records if r.get('sport') != 'Horse Racing']
    leagues = extract_leagues(football_records)
    markets = extract_markets(football_records)
    dates = sorted(str(r.get('date', ''))[:10] for r in football_records if r.get('date'))
    dates = [d for d in dates if d]
    # This page shows ACTUAL data — don't inherit the Simulation page's narrow
    # odds/date window (which silently hides high-odds markets like The Draw).
    # Open with full odds + date ranges; the user can still narrow manually.
    view_config = dict(data_store['config'])
    view_config['odds_min'] = 1.0
    view_config['odds_max'] = 100.0
    view_config['date_start'] = None
    view_config['date_end'] = None
    results = run_real_analysis(football_records, view_config)
    return render_template('analytics_real.html',
                           results=results,
                           config=view_config,
                           leagues=leagues,
                           markets=markets,
                           date_min=dates[0] if dates else '',
                           date_max=dates[-1] if dates else '')

@app.route('/settings')
def settings_page():
    records = data_store.get('data') or []
    from betfair_service import get_betfair_service
    bf = get_betfair_service()
    return render_template('settings.html', config=data_store['config'], record_count=len(records), bf_username=bf.username or '', bf_password_set=bool(bf.password))

@app.route('/horses')
def horses_page():
    records = data_store.get('data') or []
    _, hr_records = _split_records_by_sport(records)
    hr_dates = sorted(str(r.get('date', ''))[:10] for r in hr_records if r.get('date'))
    hr_dates = [d for d in hr_dates if d]
    # Count per category so the UI can show non-zero tabs
    from collections import Counter
    cat_counts = Counter(r.get('bet_category') or 'Untagged' for r in hr_records)
    return render_template('horses.html',
                           config=data_store['config'],
                           hr_tracks=extract_leagues(hr_records),
                           hr_markets=extract_markets(hr_records),
                           hr_date_min=hr_dates[0] if hr_dates else '',
                           hr_date_max=hr_dates[-1] if hr_dates else '',
                           cat_counts=dict(cat_counts))

@app.route('/today')
def today_page():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM bets WHERE substr(date,1,10) = ? ORDER BY date ASC", (today,))
    bets = [dict(row) for row in c.fetchall()]
    conn.close()
    from betfair_service import get_betfair_service
    bf = get_betfair_service()
    return render_template('today.html', bets=bets, today=today, betfair_configured=bf.is_configured(),
                           commission=data_store['config'].get('commission', 2.0))


@app.route('/api/today/pending', methods=['GET'])
def today_pending_api():
    """Return all current open/unmatched orders from Betfair (not yet settled)."""
    from betfair_service import get_betfair_service
    service = get_betfair_service()
    if not service.is_configured():
        return jsonify({'bets': [], 'message': 'Betfair not configured'})
    pending, msg = service.get_pending_orders()
    return jsonify({'bets': pending, 'message': msg})


@app.route('/api/today/refresh', methods=['POST'])
def today_refresh():
    """Delete today's Betfair records, re-pull settled history, and fetch pending orders."""
    from betfair_service import get_betfair_service
    today = datetime.now().strftime('%Y-%m-%d')

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM bets WHERE source = 'betfair' AND substr(date,1,10) = ?", (today,))
    deleted = c.rowcount
    conn.commit()
    conn.close()

    service = get_betfair_service()
    if not service.is_configured():
        return jsonify({'error': 'Betfair not configured — add credentials in Settings'}), 400

    connected, msg = service.connect()
    if not connected:
        return jsonify({'error': msg}), 400

    # Re-pull settled bets
    orders, _ = service.get_bet_history(days_back=2)
    added = 0
    if orders:
        for order in orders:
            try:
                bf_competition  = order.pop('bf_competition', '')
                bf_country_code = order.pop('bf_country_code', '')
                match           = order.get('match', '')
                country, league = get_country_league_betfair(bf_competition, bf_country_code, match)
                order['country']        = country
                order['league']         = league
                order['bf_competition'] = bf_competition
                if db_insert_bet(order, source='betfair'):
                    added += 1
            except Exception as e:
                print(f"Error re-inserting order: {e}")

        reenrich_leagues()
        reenrich_horse_racing()
        records = db_load_all()
        data_store['data']    = records
        data_store['leagues'] = extract_leagues(records)
        data_store['markets'] = extract_markets(records)

    # Settled bets for today from DB
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM bets WHERE substr(date,1,10) = ? ORDER BY date ASC", (today,))
    settled_bets = [dict(row) for row in c.fetchall()]
    conn.close()

    # Pending (open) bets from Betfair live
    pending_bets, _ = service.get_pending_orders()

    return jsonify({
        'success': True,
        'deleted': deleted,
        'added': added,
        'message': f'Deleted {deleted} old records, pulled {added} settled + {len(pending_bets)} pending from Betfair',
        'bets': settled_bets,
        'pending_bets': pending_bets,
        'today': today,
    })


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
    records = [r for r in (data_store.get('data') or []) if r.get('sport') != 'Horse Racing']
    if not records:
        return jsonify({'error': 'No data loaded'}), 400
    results = run_analysis(records, data_store['config'])
    data_store['results'] = results
    return jsonify(results)

@app.route('/api/league-profitability', methods=['POST'])
def league_profitability_api():
    """Run analysis without league filter to get per-league P&L for the current scenario."""
    config = dict(data_store['config'])
    config.update(request.json or {})
    config['selected_leagues'] = []  # no league filter — get all leagues
    records = [r for r in (data_store.get('data') or []) if r.get('sport') != 'Horse Racing']
    if not records:
        return jsonify({'league_breakdown': []})
    results = run_analysis(records, config)
    return jsonify({'league_breakdown': results.get('league_breakdown', [])})

def _odds_bucket(odds, step=0.1):
    if not odds or odds <= 0:
        return 'Unknown'
    low = round(math.floor(odds / step) * step, 1)
    high = round(low + step, 1)
    return f'{low:.1f}-{high:.1f}'

def _apply_analysis_filters(records, config):
    """Apply the same date/time/source/league/market/odds filters as run_analysis."""
    date_start = config.get('date_start') or None
    date_end = config.get('date_end') or None
    if date_start or date_end:
        filtered = []
        for r in records:
            ds = str(r.get('date', ''))[:10]
            if date_start and ds < date_start: continue
            if date_end and ds > date_end: continue
            filtered.append(r)
        records = filtered

    time_start = config.get('time_start') or None
    time_end = config.get('time_end') or None
    if time_start or time_end:
        filtered = []
        for r in records:
            date_str = str(r.get('date', ''))
            time_part = date_str[11:16] if len(date_str) >= 16 else None
            if time_part is None:
                filtered.append(r); continue
            if time_start and time_part < time_start: continue
            if time_end and time_part > time_end: continue
            filtered.append(r)
        records = filtered

    selected_sources = config.get('selected_sources') or []
    if selected_sources:
        records = [r for r in records if (r.get('source') or 'csv') in selected_sources]

    selected_leagues = config.get('selected_leagues') or []
    if selected_leagues:
        def _league_label(r): return f"{r.get('country', '')} - {r.get('league', '')}"
        def _is_unmapped(r):
            c, lg = r.get('country', ''), r.get('league', '')
            return not c or not lg or c in ('Other', 'Unknown') or lg in ('Other', 'Unknown')
        records = [r for r in records if _league_label(r) in selected_leagues or _is_unmapped(r)]

    selected_markets = config.get('selected_markets') or []
    if selected_markets:
        records = [r for r in records if normalize_bet_type(r.get('bet_type') or '') in selected_markets]

    selected_strategy_types = config.get('selected_strategy_types') or []
    if selected_strategy_types:
        records = [r for r in records if normalize_strategy_type(r.get('bet_type') or '') in selected_strategy_types]

    min_odds = float(config.get('odds_min', 1.0))
    max_odds = float(config.get('odds_max', 100.0))
    if min_odds > 1.0 or max_odds < 100.0:
        filtered = []
        for r in records:
            o = float(r.get('odds') or calc_odds(r.get('pnl', 0), r.get('stake', 0), r.get('bet_type', '')))
            if min_odds <= o <= max_odds:
                filtered.append(r)
        records = filtered

    return records

@app.route('/api/analyze/breakdown', methods=['POST'])
def analyze_breakdown_api():
    config = request.json or {}
    group_by = [g for g in (config.get('group_by') or ['odds_range']) if g]
    if not group_by:
        group_by = ['odds_range']

    records = [r for r in (data_store.get('data') or []) if r.get('sport') != 'Horse Racing']
    if not records:
        return jsonify({'rows': [], 'group_by': group_by})

    records = _apply_analysis_filters(records, config)

    base_stake = float(config.get('base_stake', 20))
    commission = float(config.get('commission', 0)) / 100.0

    # key = tuple of dimension values; value stores dims list + stats
    groups = {}

    DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    for r in records:
        status = str(r.get('status', '')).strip()
        if status not in ('Settled', 'WON', 'LOST'):
            continue

        hist_pnl = float(r.get('pnl', 0) or 0)
        odds = float(r.get('odds') or calc_odds(hist_pnl, r.get('stake', 0), r.get('bet_type', '')))

        if hist_pnl > 0:
            scaled_pnl = round(base_stake * (odds - 1) * (1.0 - commission), 2)
        elif hist_pnl < 0:
            scaled_pnl = -base_stake
        else:
            continue  # void

        dim_values = []   # display values per dimension
        sort_values = []  # sort keys per dimension
        for dim in group_by:
            if dim == 'odds_range':
                bucket = _odds_bucket(odds)
                dim_values.append(bucket)
                try:
                    sort_values.append(f'{float(bucket.split("-")[0]):08.3f}')
                except Exception:
                    sort_values.append(bucket)
            elif dim == 'league':
                lbl = f"{r.get('country', 'Other')} - {r.get('league', 'Other')}"
                dim_values.append(lbl); sort_values.append(lbl)
            elif dim == 'bet_type':
                bt = normalize_bet_type(r.get('bet_type') or '') or 'Unknown'
                dim_values.append(bt); sort_values.append(bt)
            elif dim == 'month':
                m = str(r.get('date', ''))[:7] or 'Unknown'
                dim_values.append(m); sort_values.append(m)
            elif dim == 'day_of_week':
                try:
                    dt = datetime.strptime(str(r.get('date', ''))[:10], '%Y-%m-%d')
                    day = dt.strftime('%A')
                except Exception:
                    day = 'Unknown'
                dim_values.append(day)
                sort_values.append(f'{DAY_ORDER.index(day):02d}' if day in DAY_ORDER else day)

        key = tuple(dim_values)
        sort_key = ' | '.join(sort_values)
        if key not in groups:
            groups[key] = {'dims': list(dim_values), '_sort_key': sort_key,
                           'bets': 0, 'won': 0, 'lost': 0, 'pnl': 0.0, 'stake': 0.0}
        g = groups[key]
        g['bets'] += 1
        g['stake'] += base_stake
        g['pnl'] = round(g['pnl'] + scaled_pnl, 2)
        if scaled_pnl > 0:
            g['won'] += 1
        else:
            g['lost'] += 1

    rows = []
    for g in sorted(groups.values(), key=lambda x: x['_sort_key']):
        bets = g['bets']
        win_rate = round((g['won'] / bets) * 100, 1) if bets > 0 else 0
        roi = round((g['pnl'] / g['stake']) * 100, 2) if g['stake'] > 0 else 0
        rows.append({
            'dims': g['dims'],
            'bets': bets,
            'won': g['won'],
            'lost': g['lost'],
            'win_rate': win_rate,
            'total_stake': round(g['stake'], 2),
            'pnl': round(g['pnl'], 2),
            'roi': roi,
        })

    return jsonify({'rows': rows, 'group_by': group_by})

@app.route('/api/analyze-real', methods=['POST'])
def run_real_analysis_api():
    config = request.json or {}
    records = [r for r in (data_store.get('data') or []) if r.get('sport') != 'Horse Racing']
    if not records:
        return jsonify({'error': 'No data loaded'}), 400
    results = run_real_analysis(records, config)
    return jsonify(results)

@app.route('/api/analyze-real/breakdown', methods=['POST'])
def analyze_real_breakdown_api():
    config = request.json or {}
    group_by = [g for g in (config.get('group_by') or ['odds_range']) if g]
    if not group_by:
        group_by = ['odds_range']

    records = [r for r in (data_store.get('data') or []) if r.get('sport') != 'Horse Racing']
    if not records:
        return jsonify({'rows': [], 'group_by': group_by})

    records = _apply_analysis_filters(records, config)
    commission = float(config.get('commission', 2.0)) / 100.0

    groups = {}
    DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    for r in records:
        status = str(r.get('status', '')).strip()
        if status not in ('Settled', 'WON', 'LOST'):
            continue
        raw_pnl = float(r.get('pnl', 0) or 0)
        pnl = round(raw_pnl * (1.0 - commission), 2) if raw_pnl > 0 else raw_pnl
        stake = float(r.get('stake', 0) or 0)
        odds = float(r.get('odds') or 0)

        dim_values = []
        sort_values = []
        for dim in group_by:
            if dim == 'odds_range':
                bucket = _odds_bucket(odds) if odds > 0 else 'Unknown'
                dim_values.append(bucket)
                try:
                    sort_values.append(f'{float(bucket.split("-")[0]):08.3f}')
                except Exception:
                    sort_values.append(bucket)
            elif dim == 'league':
                lbl = f"{r.get('country', 'Other')} - {r.get('league', 'Other')}"
                dim_values.append(lbl); sort_values.append(lbl)
            elif dim == 'bet_type':
                bt = normalize_bet_type(r.get('bet_type') or '') or 'Unknown'
                dim_values.append(bt); sort_values.append(bt)
            elif dim == 'month':
                m = str(r.get('date', ''))[:7] or 'Unknown'
                dim_values.append(m); sort_values.append(m)
            elif dim == 'day_of_week':
                try:
                    dt = datetime.strptime(str(r.get('date', ''))[:10], '%Y-%m-%d')
                    day = dt.strftime('%A')
                except Exception:
                    day = 'Unknown'
                dim_values.append(day)
                sort_values.append(f'{DAY_ORDER.index(day):02d}' if day in DAY_ORDER else day)

        key = tuple(dim_values)
        sort_key = ' | '.join(sort_values)
        if key not in groups:
            groups[key] = {'dims': list(dim_values), '_sort_key': sort_key,
                           'bets': 0, 'won': 0, 'lost': 0, 'pnl': 0.0, 'stake': 0.0,
                           'members': []}
        g = groups[key]
        g['bets'] += 1
        g['pnl'] = round(g['pnl'] + pnl, 2)
        g['stake'] += stake
        if pnl > 0:
            g['won'] += 1
        elif pnl < 0:
            g['lost'] += 1
        g['members'].append({
            'date': str(r.get('date', ''))[:10],
            'match': r.get('match', '') or '',
            'bet_type': r.get('bet_type', '') or '',
            'odds': round(odds, 2) if odds else 0,
            'pnl': round(pnl, 2),
            'result': 'WON' if pnl > 0 else ('LOST' if pnl < 0 else 'VOID'),
            'correct_score': r.get('correct_score') or '',
            'correct_score_status': r.get('correct_score_status') or '',
        })

    rows = []
    for g in sorted(groups.values(), key=lambda x: x['_sort_key']):
        bets = g['bets']
        win_rate = round((g['won'] / bets) * 100, 1) if bets > 0 else 0
        roi = round((g['pnl'] / g['stake']) * 100, 2) if g['stake'] > 0 else 0
        members = sorted(g['members'], key=lambda m: m['date'], reverse=True)
        rows.append({
            'dims': g['dims'], 'bets': bets, 'won': g['won'], 'lost': g['lost'],
            'win_rate': win_rate, 'total_stake': round(g['stake'], 2),
            'pnl': round(g['pnl'], 2), 'roi': roi, 'members': members,
        })
    return jsonify({'rows': rows, 'group_by': group_by})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    if file.filename.lower().endswith('.pdf'):
        bets, error = parse_pdf(filepath)
        if error:
            return jsonify({'error': error}), 500
        conn = get_db()
        conn.execute("DELETE FROM bets WHERE source = 'pdf'")
        conn.commit()
        conn.close()
        added = sum(1 for bet in bets if db_insert_bet(bet, source='pdf'))
        records = db_load_all()
        data_store['data'] = records
        data_store['leagues'] = extract_leagues(records)
        data_store['markets'] = extract_markets(records)
        return jsonify({'success': True, 'type': 'pdf', 'extracted': len(bets), 'added': added, 'total': len(records)})
    elif file.filename.lower().endswith('.csv'):
        added = load_csv_data(filepath)
        records = db_load_all()
        data_store['data'] = records
        data_store['leagues'] = extract_leagues(records)
        data_store['markets'] = extract_markets(records)
        return jsonify({'success': True, 'type': 'csv', 'added': added, 'total': len(records), 'leagues': data_store['leagues']})
    else:
        return jsonify({'error': 'Please upload a CSV or PDF file'}), 400

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
    # Record tombstones BEFORE deleting so we can prevent re-import
    db_tombstone_ids(ids)
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

@app.route('/api/leagues-list', methods=['GET'])
def leagues_list_api():
    """Return all distinct leagues for the league update dropdown."""
    records = data_store.get('data') or []
    leagues = extract_leagues(records)
    return jsonify(leagues)

@app.route('/api/bulk-update-league', methods=['POST'])
def bulk_update_league_api():
    """Update league and country for selected bets."""
    data = request.json or {}
    ids = data.get('ids', [])
    new_country = data.get('country', '')
    new_league = data.get('league', '')

    if not ids or not new_country or not new_league:
        return jsonify({'error': 'Missing IDs, country, or league'}), 400

    conn = get_db()
    c = conn.cursor()
    placeholders = ','.join(['?' for _ in ids])
    c.execute(f'UPDATE bets SET country = ?, league = ? WHERE id IN ({placeholders})',
              (new_country, new_league) + tuple(ids))
    updated = c.rowcount
    conn.commit()
    conn.close()

    records = db_load_all()
    data_store['data'] = records
    data_store['leagues'] = extract_leagues(records)
    data_store['markets'] = extract_markets(records)
    return jsonify({'success': True, 'updated': updated})


@app.route('/api/auto-detect-league', methods=['POST'])
def auto_detect_league_api():
    """Detect league for selected bets without saving. Returns per-bet results + consensus."""
    from collections import Counter
    data = request.json or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'error': 'No IDs provided'}), 400

    conn = get_db()
    c = conn.cursor()
    placeholders = ','.join('?' for _ in ids)
    c.execute(f'SELECT id, match, source FROM bets WHERE id IN ({placeholders})', ids)
    rows = c.fetchall()
    conn.close()

    results = []
    for row in rows:
        country, league, method, confidence = auto_detect_league_smart(
            row['match'] or '', row['source'] or '')
        results.append({
            'id': row['id'], 'match': row['match'] or '',
            'country': country, 'league': league,
            'method': method, 'confidence': confidence,
        })

    non_other = [r for r in results if r['country'] != 'Other']
    consensus = None
    if non_other:
        counter = Counter((r['country'], r['league']) for r in non_other)
        (cc, cl), _ = counter.most_common(1)[0]
        rep = next(r for r in non_other if r['country'] == cc and r['league'] == cl)
        consensus = {
            'country': cc, 'league': cl,
            'method': rep['method'], 'confidence': rep['confidence'],
            'matched': counter[(cc, cl)], 'total': len(results),
        }

    return jsonify({'results': results, 'consensus': consensus})


@app.route('/api/bulk-auto-detect', methods=['POST'])
def bulk_auto_detect_api():
    """Auto-detect and save league for all unclassified (Other/Unknown/blank) bets."""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id, match, source FROM bets "
        "WHERE country IN ('Other','Unknown','') OR league IN ('Other','Unknown','') "
        "OR country IS NULL OR league IS NULL"
    )
    rows = c.fetchall()
    updated = 0
    for row in rows:
        country, league, _method, _conf = auto_detect_league_smart(
            row['match'] or '', row['source'] or '')
        if country != 'Other':
            c.execute('UPDATE bets SET country=?, league=? WHERE id=?',
                      (country, league, row['id']))
            updated += 1
    conn.commit()
    conn.close()

    records = db_load_all()
    data_store['data'] = records
    data_store['leagues'] = extract_leagues(records)
    data_store['markets'] = extract_markets(records)
    return jsonify({'success': True, 'updated': updated, 'checked': len(rows)})

@app.route('/api/team-map/add', methods=['POST'])
def team_map_add():
    """Save user-defined team→country/league mappings to DB and update in-memory TEAM_MAP."""
    data = request.json or {}
    teams = data.get('teams', [])
    country = (data.get('country') or '').strip()
    league = (data.get('league') or '').strip()
    if not teams or not country or not league:
        return jsonify({'error': 'Missing teams, country, or league'}), 400
    conn = get_db()
    c = conn.cursor()
    saved = 0
    for team in teams:
        key = team.lower().strip()
        if not key:
            continue
        c.execute(
            'INSERT OR REPLACE INTO custom_team_map (team_name, country, league) VALUES (?, ?, ?)',
            (key, country, league)
        )
        TEAM_MAP[key] = (country, league)
        saved += 1
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'saved': saved})


# ==================== HORSE RACING API ====================

@app.route('/api/horses/set-category', methods=['POST'])
def horses_set_category():
    """Set bet_category for one or more horse racing bets."""
    data = request.json or {}
    ids = data.get('ids', [])
    category = (data.get('category') or '').strip() or None  # None clears the category

    if not ids:
        return jsonify({'error': 'No ids provided'}), 400
    valid = {None, 'Win', 'Place', 'EW'}
    if category not in valid:
        return jsonify({'error': f'category must be one of {valid}'}), 400

    conn = get_db()
    c = conn.cursor()
    placeholders = ','.join('?' for _ in ids)
    c.execute(f'UPDATE bets SET bet_category=? WHERE id IN ({placeholders})', [category, *ids])
    conn.commit()
    conn.close()

    # Refresh in-memory store
    records = db_load_all()
    data_store['data'] = records
    return jsonify({'updated': len(ids), 'category': category})


@app.route('/api/horses/analysis', methods=['POST'])
def horses_analysis():
    cfg = request.json or {}
    base_stake      = float(cfg.get('base_stake', 10))
    starting_bank   = float(cfg.get('starting_bank', 100))
    commission      = float(cfg.get('commission', 0)) / 100.0
    date_from       = cfg.get('date_from', '')
    date_to         = cfg.get('date_to', '')
    selected_tracks = cfg.get('selected_tracks') or []
    selected_markets = cfg.get('selected_markets') or []
    bet_category    = cfg.get('bet_category', '')   # 'Win', 'Place', 'EW', or ''
    odds_min        = float(cfg.get('odds_min', 1.0))
    odds_max        = float(cfg.get('odds_max', 1000.0))

    records = [r for r in (data_store.get('data') or []) if r.get('sport') == 'Horse Racing']

    if date_from:
        records = [r for r in records if str(r.get('date', ''))[:10] >= date_from]
    if date_to:
        records = [r for r in records if str(r.get('date', ''))[:10] <= date_to]
    if selected_tracks:
        def _track_label(r):
            return f"{r.get('country', '')} - {r.get('league', '')}"
        records = [r for r in records if _track_label(r) in selected_tracks]
    if selected_markets:
        records = [r for r in records if normalize_bet_type(r.get('bet_type') or '') in selected_markets]
    if bet_category:
        records = [r for r in records if (r.get('bet_category') or '') == bet_category]
    if odds_min > 1.0 or odds_max < 1000.0:
        records = [r for r in records
                   if odds_min <= float(r.get('odds') or 0) <= odds_max]

    records = sorted(records, key=lambda r: str(r.get('date', '')))

    bank = starting_bank
    wins = losses = 0
    total_staked = 0.0
    cat_pnl = {}   # bet_category -> cumulative scaled pnl
    bets_out = []

    for r in records:
        odds        = float(r.get('odds') or 0)
        actual_pnl  = float(r.get('pnl') or 0)
        status      = str(r.get('status') or '').strip()

        # Use actual P&L sign to determine outcome (handles place markets where
        # status is always "Settled" regardless of win/loss)
        if actual_pnl > 0:
            gross = base_stake * (odds - 1)
            pnl   = round(gross * (1 - commission), 2)
            wins += 1
        elif actual_pnl < 0:
            pnl = -base_stake
            losses += 1
        else:
            # P&L is zero — void bet, skip from staking calculation
            continue

        total_staked += base_stake
        bank = round(bank + pnl, 2)

        cat = r.get('bet_category') or ''
        cat_pnl[cat] = round(cat_pnl.get(cat, 0.0) + pnl, 2)

        country_v = r.get('country') or ''
        league_v  = r.get('league') or ''
        bets_out.append({
            'id':           r.get('id'),
            'date':         r.get('date', ''),
            'race':         r.get('match', ''),
            'selection':    r.get('bet_type', ''),
            'track':        (f"{country_v} / {league_v}" if country_v and league_v
                             else (league_v or country_v or '')),
            'odds':         odds,
            'stake':        base_stake,
            'status':       status,
            'pnl':          pnl,
            'bank':         bank,
            'bet_category': cat,
        })

    total_bets = wins + losses
    total_pnl  = round(bank - starting_bank, 2)
    win_rate   = round(wins / total_bets * 100, 1) if total_bets else 0
    roi        = round(total_pnl / total_staked * 100, 1) if total_staked else 0

    # Daily breakdown — bets_out is already in date order
    daily = {}
    for b in bets_out:
        dkey = (b.get('date') or '')[:10]
        d = daily.setdefault(dkey, {
            'date': dkey, 'bets': 0, 'won': 0, 'lost': 0,
            'staked': 0.0, 'pnl': 0.0, 'win_pnl': 0.0, 'place_pnl': 0.0,
            'start_bank': b['bank'] - b['pnl'], 'end_bank': 0.0,
        })
        d['bets']   += 1
        if b['pnl'] > 0: d['won']  += 1
        else:            d['lost'] += 1
        d['staked'] = round(d['staked'] + b['stake'], 2)
        d['pnl']    = round(d['pnl']    + b['pnl'],   2)
        if b['bet_category'] == 'Win':
            d['win_pnl']   = round(d['win_pnl']   + b['pnl'], 2)
        elif b['bet_category'] == 'Place':
            d['place_pnl'] = round(d['place_pnl'] + b['pnl'], 2)
        d['end_bank'] = b['bank']
    daily_results = [daily[k] for k in sorted(daily.keys())]

    return jsonify({
        'bets': bets_out,
        'daily_results': daily_results,
        'summary': {
            'total_bets':   total_bets,
            'wins':         wins,
            'losses':       losses,
            'win_rate':     win_rate,
            'total_pnl':    total_pnl,
            'win_pnl':      round(cat_pnl.get('Win', 0.0), 2),
            'place_pnl':    round(cat_pnl.get('Place', 0.0), 2),
            'roi':          roi,
            'final_bank':   round(bank, 2),
            'total_staked': round(total_staked, 2),
        }
    })

# ==================== BETFAIR API ====================

@app.route('/api/betfair/status', methods=['GET'])
def betfair_status():
    """Check Betfair connection status"""
    from betfair_service import get_betfair_service
    service = get_betfair_service()
    return jsonify({
        'configured': service.is_configured(),
        'connected': service._trading is not None if service else False
    })

@app.route('/api/betfair/connect', methods=['POST'])
def betfair_connect():
    """Save Betfair credentials and test connection"""
    from betfair_service import get_betfair_service
    data = request.json

    service = get_betfair_service()
    # Use existing stored values for any field left blank by the user
    username = data.get('username') or service.username
    password = data.get('password') or service.password
    app_key = data.get('app_key') or service.app_key

    success = service.save_credentials(username=username, password=password, app_key=app_key)

    if success:
        connected, msg = service.connect()
        return jsonify({'success': connected, 'message': msg})

    return jsonify({'success': False, 'message': 'Failed to save credentials'}), 400

def enrich_correct_scores(retry_unavailable=False, max_lookups=None):
    """Persist final scorelines onto football bets, sourced from TheSportsDB.

    Bets are grouped by (date, match) so one API call per date resolves every
    bet on that match. Idempotent: groups already resolved ('exact') are skipped.
    By default groups previously marked 'unavailable' are also skipped (so routine
    syncs stay cheap); pass retry_unavailable=True to re-attempt them — useful after
    adding a premium TheSportsDB key in Settings.

    Returns the number of matches resolved to an actual score this run.
    """
    api_key = (data_store.get('config') or {}).get('sportsdb_key') or '3'
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id, date, match, correct_score_status FROM bets WHERE sport='Football'"
    )
    rows = c.fetchall()

    # Group bet ids by (date_day, match); decide which groups still need a lookup.
    groups = {}   # (date_day, match) -> {'ids': [...], 'has_exact': bool, 'has_null': bool}
    for row in rows:
        date_day = str(row['date'] or '')[:10]
        match = (row['match'] or '').strip()
        if not date_day or not match or match == 'Unknown':
            continue
        g = groups.setdefault((date_day, match),
                              {'ids': [], 'has_exact': False, 'has_null': False})
        g['ids'].append(row['id'])
        st = (row['correct_score_status'] or '')
        if st == 'exact':
            g['has_exact'] = True
        elif st == '':
            g['has_null'] = True

    targets = [(k, g) for k, g in groups.items()
               if not g['has_exact'] and (g['has_null'] or retry_unavailable)]

    resolved_count = 0
    processed = 0
    for (date_day, match), g in targets:
        if max_lookups and processed >= max_lookups:
            break
        processed += 1
        score = _lookup_score_sportsdb(match, date_day, api_key)
        placeholders = ','.join('?' for _ in g['ids'])
        if score:
            c.execute(
                f"UPDATE bets SET correct_score=?, correct_score_status='exact' "
                f"WHERE id IN ({placeholders})",
                [score] + g['ids'],
            )
            resolved_count += 1
        else:
            # Mark as tried, but never clobber an existing score.
            c.execute(
                f"UPDATE bets SET correct_score_status='unavailable' "
                f"WHERE id IN ({placeholders}) AND (correct_score IS NULL OR correct_score='')",
                g['ids'],
            )

    conn.commit()
    conn.close()
    return resolved_count


@app.route('/api/scores/backfill', methods=['POST'])
def scores_backfill():
    """Resolve football scorelines from TheSportsDB for all bets without one.

    Pass {"retry": true} to re-attempt matches previously marked 'unavailable'
    (e.g. after adding a premium TheSportsDB key in Settings).
    """
    data = request.json or {}
    retry = bool(data.get('retry'))
    try:
        scored = enrich_correct_scores(retry_unavailable=retry)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    records = db_load_all()
    data_store['data'] = records
    data_store['leagues'] = extract_leagues(records)
    data_store['markets'] = extract_markets(records)

    return jsonify({
        'success': True,
        'scored': scored,
        'message': (f'Resolved {scored} match score(s) from TheSportsDB'
                    if scored else 'No new scores found '
                    '(free key covers major leagues only — add a premium key in Settings)')
    })


@app.route('/api/betfair/sync', methods=['POST'])
def betfair_sync():
    """Sync betting history from Betfair"""
    from betfair_service import get_betfair_service
    data = request.json
    days_back = data.get('days_back', 30)
    
    service = get_betfair_service()
    
    if not service.is_configured():
        return jsonify({'error': 'Betfair not configured. Please add credentials in Settings.'}), 400
    
    # Connect to Betfair
    connected, msg = service.connect()
    if not connected:
        return jsonify({'error': msg}), 400
    
    # Get bet history
    orders, history_msg = service.get_bet_history(days_back)
    
    if not orders:
        return jsonify({
            'message': history_msg,
            'added': 0,
            'note': 'Certificate authentication required for full API access. You can also upload CSV files manually.'
        })
    
    # Add orders to database
    added = 0
    for order in orders:
        try:
            match = order.get('match', '')
            bf_competition  = order.pop('bf_competition', '')
            bf_country_code = order.pop('bf_country_code', '')
            country, league = get_country_league_betfair(bf_competition, bf_country_code, match)
            order['country']        = country
            order['league']         = league
            order['bf_competition'] = bf_competition  # stored for future re-enrichment
            if db_insert_bet(order, source='betfair'):
                added += 1
        except Exception as e:
            print(f"Error adding betfair order: {e}")
            continue
    
    reenrich_leagues()
    reenrich_horse_racing()
    reenrich_football_bet_categories()

    # Resolve final scorelines for football bets from TheSportsDB.
    scored = 0
    try:
        scored = enrich_correct_scores()
    except Exception as e:
        print(f"Correct score enrichment failed: {e}")

    records = db_load_all()
    data_store['data'] = records
    data_store['leagues'] = extract_leagues(records)
    data_store['markets'] = extract_markets(records)

    msg = f'Added {added} bets from Betfair'
    if scored:
        msg += f'; resolved {scored} match scores'
    return jsonify({
        'success': True,
        'added': added,
        'scored': scored,
        'message': msg
    })


@app.route('/api/betfair/refresh-hr-today', methods=['POST'])
def betfair_refresh_hr_today():
    """Delete today's Betfair HR records and re-pull fresh from Betfair."""
    from betfair_service import get_betfair_service

    today = datetime.now().strftime('%Y-%m-%d')

    # Delete today's HR betfair records directly — no tombstone so they can be re-imported
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "DELETE FROM bets WHERE sport = 'Horse Racing' AND source = 'betfair' AND substr(date,1,10) = ?",
        (today,)
    )
    deleted = c.rowcount
    conn.commit()
    conn.close()

    # Re-sync — 2 days covers today; duplicate detection rejects anything already in DB
    service = get_betfair_service()
    if not service.is_configured():
        return jsonify({'error': 'Betfair not configured'}), 400

    connected, msg = service.connect()
    if not connected:
        return jsonify({'error': msg}), 400

    orders, history_msg = service.get_bet_history(days_back=2)
    if not orders:
        return jsonify({'deleted': deleted, 'added': 0, 'message': history_msg})

    added = 0
    for order in orders:
        try:
            bf_competition  = order.pop('bf_competition', '')
            bf_country_code = order.pop('bf_country_code', '')
            match           = order.get('match', '')
            country, league = get_country_league_betfair(bf_competition, bf_country_code, match)
            order['country']        = country
            order['league']         = league
            order['bf_competition'] = bf_competition
            if db_insert_bet(order, source='betfair'):
                added += 1
        except Exception as e:
            print(f"Error re-inserting order: {e}")

    reenrich_leagues()
    reenrich_horse_racing()
    records = db_load_all()
    data_store['data']    = records
    data_store['leagues'] = extract_leagues(records)
    data_store['markets'] = extract_markets(records)

    return jsonify({
        'success': True,
        'deleted': deleted,
        'added':   added,
        'message': f'Deleted {deleted} old records, re-imported {added} from Betfair'
    })


@app.route('/api/betfair/reenrich-from-betfair', methods=['POST'])
def betfair_reenrich_from_betfair():
    """Re-fetch Betfair order history and update country/league/bf_competition for
    existing records where the Betfair competition name provides a better classification
    than what is currently stored (or where no classification was set).
    """
    from betfair_service import get_betfair_service
    data = request.json or {}
    days_back = int(data.get('days_back', 90))

    service = get_betfair_service()
    if not service.is_configured():
        return jsonify({'error': 'Betfair not configured'}), 400

    connected, msg = service.connect()
    if not connected:
        return jsonify({'error': msg}), 400

    orders, history_msg = service.get_bet_history(days_back)
    if not orders:
        return jsonify({'error': history_msg or 'No orders found in period'}), 400

    conn = get_db()
    c = conn.cursor()
    updated = 0
    checked = 0

    for order in orders:
        bf_competition  = order.get('bf_competition', '')
        bf_country_code = order.get('bf_country_code', '')
        order_sport     = order.get('sport', '')
        order_market    = order.get('market', '')
        bf_raw_data     = order.get('bf_raw_data', '')

        match    = order.get('match', '') or ''
        date_str = str(order.get('date', ''))[:10]

        # Derive country/league when competition is known
        country = league = None
        if bf_competition:
            c_val, l_val = get_country_league_betfair(bf_competition, bf_country_code, match)
            if c_val != 'Other':
                country, league = c_val, l_val

        try:
            dt        = datetime.strptime(date_str, '%Y-%m-%d')
            date_from = (dt - timedelta(days=1)).strftime('%Y-%m-%d')
            date_to   = (dt + timedelta(days=1)).strftime('%Y-%m-%d')
        except Exception:
            date_from = date_to = date_str

        norm_match = normalize_match_name(match)

        c.execute(
            "SELECT id, match, country, league, sport, market, bet_category FROM bets "
            "WHERE substr(date,1,10) >= ? AND substr(date,1,10) <= ? AND source='betfair'",
            (date_from, date_to)
        )
        for db_id, db_match, cur_country, cur_league, cur_sport, cur_market, cur_bet_cat in c.fetchall():
            checked += 1
            if normalize_match_name(str(db_match or '')) != norm_match:
                continue

            updates = {}
            if country and (cur_country != country or cur_league != league):
                updates['country'] = country
                updates['league'] = league
                updates['bf_competition'] = bf_competition
            # Update sport if Betfair now provides it authoritatively
            if order_sport and cur_sport != order_sport:
                updates['sport'] = order_sport
            # Update market field if it's still the generic 'Exchange' placeholder
            if order_market and order_market != 'Exchange' and cur_market == 'Exchange':
                updates['market'] = order_market
            # Clear bet_category for football records
            if order_sport == 'Football' and cur_bet_cat is not None:
                updates['bet_category'] = None
            # Always update raw data with fresh metrics
            if bf_raw_data:
                updates['bf_raw_data'] = bf_raw_data

            if not updates:
                continue
            set_clause = ', '.join(f"{k}=?" for k in updates)
            c.execute(
                f"UPDATE bets SET {set_clause} WHERE id=?",
                list(updates.values()) + [db_id]
            )
            updated += 1

    conn.commit()
    conn.close()

    # Also run the local football cleanup pass
    reenrich_football_bet_categories()

    # Backfill final scorelines for football bets from TheSportsDB.
    scored = 0
    try:
        scored = enrich_correct_scores()
    except Exception as e:
        print(f"Correct score enrichment failed: {e}")

    # Reload in-memory store
    records = db_load_all()
    data_store['data'] = records
    data_store['leagues'] = extract_leagues(records)
    data_store['markets'] = extract_markets(records)

    msg = f'Updated {updated} records using Betfair competition data'
    if scored:
        msg += f'; resolved {scored} match scores'
    return jsonify({
        'success': True,
        'updated': updated,
        'scored': scored,
        'message': msg
    })


# ==================== PLACE BETS PAGE ====================

@app.route('/place-bets')
def place_bets_page():
    from betfair_service import get_betfair_service
    service = get_betfair_service()
    return render_template(
        'place_bets.html',
        betfair_configured=service.is_configured(),
        betfair_connected=bool(service._trading and service._trading.session_token),
    )


@app.route('/api/betfair/search-runners', methods=['POST'])
def search_runners_api():
    """Search Betfair for a horse in upcoming WIN/PLACE markets."""
    from betfair_service import get_betfair_service
    data = request.json or {}

    horse_name = (data.get('horse_name') or '').strip().replace("'", "")
    venue      = (data.get('venue') or '').strip()
    race_date  = (data.get('date') or '').strip()
    race_time  = (data.get('time') or '').strip()

    if not horse_name:
        return jsonify({'error': 'horse_name is required'}), 400

    service = get_betfair_service()
    if not service.is_configured():
        return jsonify({'error': 'Betfair not configured — add credentials in Settings'}), 400

    catalogues, msg = service.search_horse_racing_markets(
        venue=venue or None,
        race_date=race_date or None,
        race_time=race_time or None,
    )
    if catalogues is None:
        return jsonify({'error': msg}), 400

    matches = service.find_runner(horse_name, catalogues)

    # If user supplied a time, prefer markets whose start_time contains that time
    if race_time and matches:
        time_str = race_time.replace(':', '')[:4]  # "1430"
        preferred = [m for m in matches if m.get('start_time', '').replace(':', '').find(time_str) >= 0]
        if preferred:
            matches = preferred

    # Enrich with real market description data for accurate place counts / EW terms.
    # Targeted call on specific market IDs — no TOO_MUCH_DATA risk.
    if matches:
        market_ids = {m['market_id'] for m in matches}
        descriptions = service.get_market_descriptions(market_ids)
        for m in matches:
            desc = descriptions.get(m['market_id'], {})
            if m.get('market_type') == 'PLACE':
                now = desc.get('number_of_winners') or 0
                m['place_count'] = now if now > 0 else None
            elif m.get('market_type') == 'WIN':
                m['ew_divisor'] = desc.get('each_way_divisor')
                m['ew_places'] = _parse_ew_places_from_rules(desc.get('rules') or '')

    return jsonify({'found': bool(matches), 'matches': matches})


@app.route('/api/betfair/place-bets', methods=['POST'])
def place_bets_api():
    """Place bets on Betfair Exchange."""
    from betfair_service import get_betfair_service
    data = request.json or {}
    bets = data.get('bets', [])
    for bet in bets:
        if 'horse_name' in bet:
            bet['horse_name'] = str(bet.get('horse_name', '')).replace("'", "")

    if not bets:
        return jsonify({'error': 'No bets provided'}), 400

    service = get_betfair_service()
    if not service.is_configured():
        return jsonify({'error': 'Betfair not configured'}), 400

    results, msg = service.place_exchange_bets(bets)
    if results is None:
        return jsonify({'error': msg}), 400

    successes = sum(1 for r in results if r.get('status') == 'SUCCESS')
    return jsonify({'success': True, 'placed': successes, 'total': len(results), 'results': results})


# ==================== DAILY PICKS ====================

@app.route('/api/picks/files', methods=['GET'])
def list_picks_files():
    """List CSV files in the configured picks folder."""
    picks_folder = Path(data_store['config'].get('picks_folder', 'picks'))
    picks_folder.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(picks_folder.glob('*.csv'), key=lambda x: x.stat().st_mtime, reverse=True):
        files.append({'name': f.name, 'modified': f.stat().st_mtime})
    return jsonify({'folder': str(picks_folder.resolve()), 'files': files})


@app.route('/api/picks/load', methods=['GET'])
def load_picks_file():
    """Parse a picks CSV from the picks folder and return structured picks."""
    import csv as csv_mod
    picks_folder = Path(data_store['config'].get('picks_folder', 'picks'))
    picks_folder.mkdir(parents=True, exist_ok=True)

    requested = request.args.get('file', '').strip()
    if requested:
        target = picks_folder / requested
        if not target.exists():
            return jsonify({'error': f'File not found: {requested}'}), 404
    else:
        today_str = datetime.now().strftime('%y%m%d')
        csv_files = sorted(picks_folder.glob('*.csv'), key=lambda f: f.stat().st_mtime, reverse=True)
        today_files = [f for f in csv_files if today_str in f.stem]
        target = today_files[0] if today_files else (csv_files[0] if csv_files else None)

    if not target:
        return jsonify({'picks': [], 'file': None,
                        'message': f'No CSV files in {picks_folder.resolve()} — drop your picks file there'})

    today_iso = datetime.now().strftime('%Y-%m-%d')
    picks = []
    try:
        with open(target, newline='', encoding='utf-8-sig') as f:
            reader = csv_mod.DictReader(f)
            for row in reader:
                norm = {k.strip().lower(): (v or '').strip() for k, v in row.items()}
                horse  = norm.get('horse', '')
                course = norm.get('course') or norm.get('venue') or ''
                time_raw = norm.get('time', '')
                date_raw = norm.get('date', '')
                rank     = norm.get('rank', '')
                ml_prob  = norm.get('ml_prob', '')
                if not horse:
                    continue
                # Date: YYMMDD or YYYYMMDD -> ISO
                date_iso = today_iso
                d = date_raw.replace('-', '').replace('/', '')
                if len(d) == 6 and d.isdigit():
                    date_iso = f'20{d[:2]}-{d[2:4]}-{d[4:]}'
                elif len(d) == 8 and d.isdigit():
                    date_iso = f'{d[:4]}-{d[4:6]}-{d[6:]}'
                # Time: HHMM or HH:MM -> HH:MM
                t = time_raw.replace(':', '')
                time_fmt = f'{t[:2]}:{t[2:]}' if len(t) == 4 and t.isdigit() else (time_raw[:5] if ':' in time_raw else '')
                picks.append({'horse': horse, 'course': course, 'time': time_fmt,
                              'date': date_iso, 'rank': rank, 'ml_prob': ml_prob})
        n = len(picks)
        return jsonify({'picks': picks, 'file': target.name,
                        'message': f'Loaded {n} pick{"s" if n != 1 else ""} from {target.name}'})
    except Exception as e:
        return jsonify({'error': f'Error reading {target.name}: {e}'}), 400


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

def migrate_sport_column():
    """Classify existing records that have no sport set."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, match, bet_type, market, league FROM bets WHERE sport IS NULL")
    rows = c.fetchall()
    for row in rows:
        record = {'match': row[1], 'bet_type': row[2], 'market': row[3], 'league': row[4]}
        # detect_sport() may return None for ambiguous rows (Golf/Tennis outrights
        # use 'Win'/'Each Way' markets identically to HR). Default NULL rows to
        # Football — they're legacy CSV/PDF imports which are all football.
        sport = detect_sport(record) or 'Football'
        c.execute("UPDATE bets SET sport = ? WHERE id = ?", (sport, row[0]))
    conn.commit()
    conn.close()
    return len(rows)


def _parse_ew_places_from_rules(rules_text):
    """Extract the number of EW places from a Betfair WIN market rules string.

    Betfair rules text is often HTML.  Patterns seen in practice:
      "EACH WAY: 1/5 OF THE WIN ODDS - 3 PLACES"
      "Each Way: 1/4 odds - 3 places"
      "each way 1/5 3 places"
    Returns an int (2-5) or None if not found.
    """
    if not rules_text:
        return None
    # Strip HTML tags and decode common entities so regex works cleanly
    text = re.sub(r'<[^>]+>', ' ', rules_text)
    text = re.sub(r'&nbsp;', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'&[a-z]+;', ' ', text)
    # Look for digit 2-5 near the word "place(s)"
    m = re.search(r'\b([2-5])\s+places?\b', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    # Alternative order: "places: 3" or "places 3"
    m = re.search(r'\bplaces?\s*[:\-]?\s*([2-5])\b', text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _extract_hr_track(match_str):
    """From a match string like '16:25 Yarmouth' return the track name, or None."""
    import re
    s = (match_str or '').strip()
    # Strip leading time e.g. "16:25 " or "4:25 "
    s = re.sub(r'^\d{1,2}:\d{2}\s*', '', s).strip()
    if s:
        return s
    return None


def reenrich_horse_racing():
    """Set country and league (track) for ALL Horse Racing records from match string.

    Uses contains-based matching so "Kempton Park (AW)" correctly maps to "Kempton".
    Sorted longest-first to avoid "york" matching inside "newyork"-style strings.
    """
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, match FROM bets WHERE sport = 'Horse Racing'")
    rows = c.fetchall()
    updated = 0
    sorted_tracks = sorted(HORSE_RACING_TRACK_COUNTRY.keys(), key=len, reverse=True)
    for row_id, match in rows:
        m_lower = (match or '').lower()
        country_val = None
        track_display = None
        for track_key in sorted_tracks:
            if track_key in m_lower:
                country_val = HORSE_RACING_TRACK_COUNTRY[track_key]
                track_display = track_key.title()
                break
        if not track_display:
            raw = _extract_hr_track(match)
            if raw:
                track_display = raw
                country_val = 'UK'
            else:
                continue
        c.execute(
            "UPDATE bets SET league = ?, country = ? WHERE id = ?",
            (track_display, country_val, row_id)
        )
        updated += 1
    conn.commit()
    conn.close()
    return updated


def reenrich_football_bet_categories():
    """Fix mis-classified football records introduced by the old HR-only bet_category logic.

    Two passes:
    1. Correct any record where detect_sport() now disagrees with the stored sport
       (catches HR bets mis-tagged Football and vice-versa from earlier syncs).
    2. Clear bet_category for Football records — Win/Place is meaningless for football
       and was incorrectly set because market_desc ('Match Odds') was non-empty.
    """
    conn = get_db()
    c = conn.cursor()

    # Pass 1: fix sport mis-labels. Only overwrite when detect_sport is *confident*
    # (returns non-None). Otherwise we'd clobber Betfair-sourced Golf/Tennis labels.
    c.execute("SELECT id, match, bet_type, market, league, sport FROM bets")
    sport_fixed = 0
    for row_id, match, bet_type, market, league, stored_sport in c.fetchall():
        rec = {'match': match, 'bet_type': bet_type, 'market': market, 'league': league}
        correct = detect_sport(rec)
        if correct is not None and correct != stored_sport:
            c.execute("UPDATE bets SET sport=? WHERE id=?", (correct, row_id))
            sport_fixed += 1

    # Pass 2: clear bet_category for football records
    c.execute(
        "UPDATE bets SET bet_category = NULL "
        "WHERE sport = 'Football' AND bet_category IS NOT NULL"
    )
    cat_fixed = c.rowcount

    conn.commit()
    conn.close()
    return sport_fixed, cat_fixed


# =============================================================================
# Strategy simulation platform (Betsoccer xlsx imports)
# =============================================================================

STRATEGY_FOLDERS = ['strategies', '.']   # scan these dirs for Betsoccer*.xlsx
STRATEGY_FILE_PREFIX = 'Betsoccer'
# Tolerant brand-prefix matcher: accepts the canonical "Betsoccer" plus common
# typos like "BetSoocer" (doubled vowel / extra consonant), the newer
# "1 BSP ..." export naming (optional leading number, "BSP" brand), and the
# "BangBetsoccer..." export (an optional "Bang" sub-brand prefix), so a
# renamed export filename is still imported rather than silently skipped.
STRATEGY_PREFIX_RE = re.compile(r'^\s*(?:\d+\s*)?(?:bang\s*)?(?:betso+c+er|bsp|youtube)', re.I)

# Canonical strategy identity. There are exactly FOUR strategies — Boost,
# Main Away, Main Home, Back Up Boost — and any number of file variants may
# exist for each (with/without spaces, with/without a "Pro" prefix, with a
# parenthesized annotation like "( Main Strat )"). Variants must collapse to
# ONE canonical key so combined selections never double-count bets and the
# newest-mtime-wins logic picks a single backing file per strategy.
STRATEGY_CANONICAL_NAMES = {
    'mainaway': 'Main Away',
    'mainhome': 'Main Home',
    'boost': 'Boost',
    'backupboost': 'Back Up Boost',
    'bang': 'Bang',
    'youtube': 'Youtube New',
}

# Strategies tracked as TWO separate systems split by the alert-time scoreline
# (the data_json 'sum_score' field). As of 2026-06, Back Up Boost is run as
# distinct home-winning (1-0) and away-winning (0-1) systems, exported as
# multiple sibling files (e.g. "...Back Up Boost (2)" + "...Back Up Boost (1-0)").
# For these keys EVERY matching file is unioned (deduped on match identity) and
# then partitioned into "<name> 1-0" / "<name> 0-1" strategy entries — newest
# file wins on conflict — so no rows are dropped and the two systems appear as
# separate selectable strategies in the UI.
SCORELINE_SPLIT_KEYS = {'backupboost'}

# Map raw xlsx group headers -> short snake_case prefixes used as JSON keys
_STRAT_GROUP_PREFIX = {
    'Match Data': 'md',
    'Alert Time Stats': 'alert',
    'Half Time Stats': 'ht',
    'Full Time Stats': 'ft',
    'Live Odds (Alert Time)': 'live',
    'Pre-Match Odds': 'pre',
    'Goal Times': 'gt',
    'Summary': 'sum',
}


def _strat_key(group, field):
    """Flatten a (group, field) header pair to a stable snake_case key."""
    prefix = _STRAT_GROUP_PREFIX.get(str(group).strip(), str(group).strip().lower())
    f = str(field).strip().lower()
    f = (f.replace('%', 'pct')
           .replace('3-way:', '3way')
           .replace(': ', '_')
           .replace(':', '_')
           .replace('-', '_')
           .replace('.', '_')
           .replace(' ', '_'))
    f = re.sub(r'_+', '_', f).strip('_')
    return f"{prefix}_{f}"


def _strategy_canonical_key(filename):
    """Format-insensitive identity key for a Betsoccer xlsx file. Spacing,
    case, parenthesized annotations (e.g. "( Main Strat )"), and an optional
    leading "Pro" sub-prefix all collapse, so all of these resolve to the
    same key 'boost':
        BetsoccerProBoost.xlsx
        BetsoccerPro Boost.xlsx
        BetSoccerProBoost ( Main Strat ).xlsx
    and 'backupboost' absorbs both BetSoccerBackUpBoost.xlsx and
    BetSoccerProBackUpBoost.xlsx, etc. There are only four strategies."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    stem = re.sub(r'\([^)]*\)', '', stem)
    # The "Bang" sub-brand is its own standalone trigger strategy, not a variant
    # of the four core strategies. Detect it before the prefix strip (which would
    # otherwise leave a meaningless trailing token like "New").
    if re.match(r'^\s*(?:\d+\s*)?bang', stem, re.I):
        return 'bang'
    # "Youtube New" is also a standalone strategy in the same xlsx format as the
    # four core strategies — detect before the prefix strip so it keeps a stable
    # 'youtube' key instead of collapsing to the trailing "New" token.
    if re.match(r'^\s*(?:\d+\s*)?youtube', stem, re.I):
        return 'youtube'
    stem = STRATEGY_PREFIX_RE.sub('', stem, count=1)
    s = stem.lstrip()
    if s.lower().startswith('pro'):
        stem = s[3:]
    k = re.sub(r'[^a-z0-9]', '', stem.lower())
    # Collapse spacing/word-order variants to the four canonical strategies, so
    # e.g. "BSPBoost Main" and "BetsoccerProBoost" both resolve to 'boost' and
    # "Back up boost" to 'backupboost' (checked first — it also contains "boost").
    if 'backup' in k:
        return 'backupboost'
    if 'boost' in k:
        return 'boost'
    if 'away' in k:
        return 'mainaway'
    if 'home' in k:
        return 'mainhome'
    return k


def _derive_strategy_name(filename):
    """Display name for a Betsoccer xlsx file. Files that resolve to the same
    canonical key share one display name regardless of spacing/case."""
    key = _strategy_canonical_key(filename)
    if key in STRATEGY_CANONICAL_NAMES:
        return STRATEGY_CANONICAL_NAMES[key]
    stem = os.path.splitext(os.path.basename(filename))[0]
    stem = STRATEGY_PREFIX_RE.sub('', stem, count=1)
    return stem.strip() or key


def _strat_clean_value(v):
    """Coerce pandas/NaN values into JSON-friendly primitives."""
    try:
        if v is None:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
        if isinstance(v, (int, float, bool)):
            return v
        if hasattr(v, 'isoformat'):
            return v.isoformat()
        s = str(v).strip()
        if s == '' or s.lower() in ('nan', 'nat'):
            return None
        return s
    except Exception:
        return None


def import_strategy_xlsx(filepath):
    """Read one Betsoccer xlsx file. Returns list of row-dicts ready for DB insert."""
    df = pd.read_excel(filepath, header=[0, 1])
    rows = []
    cols = df.columns.tolist()
    keymap = [(_strat_key(g, f), g, f) for g, f in cols]
    for _, src_row in df.iterrows():
        data = {}
        for (key, g, f), val in zip(keymap, src_row.tolist()):
            data[key] = _strat_clean_value(val)
        # Promote a few fields for indexing
        strike_raw = data.get('md_strike')
        if isinstance(strike_raw, str):
            strike = 1 if strike_raw.strip().lower() in ('true', '1', 'yes') else 0
        else:
            strike = 1 if strike_raw else 0
        rows.append({
            'alert_date': data.get('md_date'),
            'timer': data.get('md_timer'),
            'strike': strike,
            'region': data.get('md_region') or '',
            'league': data.get('md_league') or '',
            'home_team': data.get('md_home') or '',
            'away_team': data.get('md_away') or '',
            'data_json': data,
        })
    return rows


def import_all_strategies():
    """Scan known folders for Betsoccer*.xlsx and load each as a strategy.

    Files that resolve to the same canonical strategy (e.g. a spaced-name and a
    non-spaced-name export of "Main Away") are NOT loaded twice — only the
    NEWEST file per strategy is imported, so a freshly-dropped file replaces a
    stale one and combined selections never double-count the same bet. Every
    row for a strategy is replaced wholesale on import, and any strategy no
    longer backed by a file is pruned from the table."""
    base = os.path.dirname(os.path.abspath(__file__))
    # canonical key -> list of {path, fn, mtime}. Most keys use only the newest
    # file; scoreline-split keys union every sibling file (see SCORELINE_SPLIT_KEYS).
    by_key = {}
    seen_paths = set()
    for folder in STRATEGY_FOLDERS:
        folder_abs = os.path.join(base, folder) if not os.path.isabs(folder) else folder
        if not os.path.isdir(folder_abs):
            continue
        for fn in os.listdir(folder_abs):
            if not fn.lower().endswith('.xlsx'):
                continue
            if not STRATEGY_PREFIX_RE.match(fn):
                continue
            path = os.path.join(folder_abs, fn)
            real = os.path.normcase(os.path.abspath(path))
            if real in seen_paths:
                continue
            seen_paths.add(real)
            key = _strategy_canonical_key(fn)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                mtime = 0
            by_key.setdefault(key, []).append({'path': path, 'fn': fn, 'mtime': mtime})
    for files in by_key.values():
        files.sort(key=lambda i: i['mtime'], reverse=True)   # newest first

    summary = []

    def _read(info, strat_label):
        """Read one xlsx, recording a summary error (and returning None) on failure."""
        try:
            return import_strategy_xlsx(info['path'])
        except PermissionError:
            summary.append({'file': info['fn'], 'strategy': strat_label, 'imported': 0,
                            'error': 'File is open in Excel — close it and re-import.'})
        except Exception as e:
            summary.append({'file': info['fn'], 'strategy': strat_label, 'imported': 0, 'error': str(e)})
        return None

    # Build a plan of (strategy_name -> [rows]) before writing anything.
    plan = {}            # strategy name -> list of row dicts (each tagged _src)
    for key, files in by_key.items():
        if key in SCORELINE_SPLIT_KEYS:
            base_name = STRATEGY_CANONICAL_NAMES.get(key, _derive_strategy_name(files[0]['fn']))
            seen_rows = set()   # dedup union of all sibling files (newest wins)
            for info in files:
                rows = _read(info, base_name)
                if rows is None:
                    continue
                for r in rows:
                    ident = (r['alert_date'], r['timer'], r['home_team'], r['away_team'])
                    if ident in seen_rows:
                        continue
                    seen_rows.add(ident)
                    score = str((r['data_json'] or {}).get('sum_score') or '').strip() or 'unknown'
                    r['_src'] = info['fn']
                    plan.setdefault(f"{base_name} {score}", []).append(r)
        else:
            info = files[0]   # newest file wins
            strategy = _derive_strategy_name(info['fn'])
            rows = _read(info, strategy)
            if rows is None:
                continue
            for r in rows:
                r['_src'] = info['fn']
            plan.setdefault(strategy, []).extend(rows)

    # Strategies we expect to exist after this run. A file that errored on read
    # contributes no plan entry, so its old rows survive the prune below.
    expected_strategies = set(plan.keys())

    conn = get_db()
    c = conn.cursor()
    for strategy, rows in plan.items():
        # Wipe every prior row for this strategy (covers rows left behind by an
        # older sibling file or a previous naming scheme) before reloading.
        c.execute('DELETE FROM strategy_bets WHERE strategy = ?', (strategy,))
        inserted = 0
        for r in rows:
            try:
                c.execute('''INSERT OR REPLACE INTO strategy_bets
                    (strategy, source_file, alert_date, timer, strike, region, league,
                     home_team, away_team, data_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?)''',
                    (strategy, r.get('_src', ''), r['alert_date'], r['timer'], r['strike'],
                     r['region'], r['league'], r['home_team'], r['away_team'],
                     json.dumps(r['data_json'], default=str)))
                inserted += 1
            except Exception as e:
                print(f"strategy insert skipped: {e}")
        summary.append({'file': rows[0].get('_src', '') if rows else '',
                        'strategy': strategy, 'imported': inserted})

    # Drop rows for any strategy no longer backed by a file (old naming scheme,
    # deleted/renamed file). Skipped entirely if nothing imported, so a totally
    # failed scan never wipes the table.
    if expected_strategies:
        placeholders = ','.join('?' * len(expected_strategies))
        c.execute(f'DELETE FROM strategy_bets WHERE strategy NOT IN ({placeholders})',
                  tuple(expected_strategies))
    conn.commit()
    conn.close()
    return summary


def db_load_strategy_rows(strategy=None):
    conn = get_db()
    c = conn.cursor()
    if strategy and strategy.lower() != 'all':
        c.execute('SELECT * FROM strategy_bets WHERE strategy = ? ORDER BY alert_date',
                  (strategy,))
    else:
        c.execute('SELECT * FROM strategy_bets ORDER BY strategy, alert_date')
    out = []
    for r in c.fetchall():
        try:
            payload = json.loads(r['data_json']) if r['data_json'] else {}
        except Exception:
            payload = {}
        out.append({
            'id': r['id'],
            'strategy': r['strategy'],
            'source_file': r['source_file'],
            'alert_date': r['alert_date'],
            'timer': r['timer'],
            'strike': r['strike'],
            'region': r['region'],
            'league': r['league'],
            'home_team': r['home_team'],
            'away_team': r['away_team'],
            'data': payload,
        })
    conn.close()
    return out


@app.route('/strategies')
def strategies_page():
    return render_template('strategies.html')


@app.route('/api/strategies/data', methods=['GET'])
def strategies_data_api():
    strategy = request.args.get('strategy', 'all')
    rows = db_load_strategy_rows(strategy)
    # Collate strategy meta (counts, default price column)
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT strategy, COUNT(*) as n, SUM(strike) as wins FROM strategy_bets '
              'GROUP BY strategy')
    meta = [{'strategy': r['strategy'], 'count': r['n'], 'wins': r['wins']}
            for r in c.fetchall()]
    conn.close()
    return jsonify({'rows': rows, 'meta': meta, 'total': len(rows)})


@app.route('/api/strategies/reimport', methods=['POST'])
def strategies_reimport_api():
    summary = import_all_strategies()
    return jsonify({'status': 'ok', 'summary': summary})


def initialize_app():
    init_db()
    load_custom_team_map()
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
    # Re-enrich Other/Unknown records first
    enriched = reenrich_leagues()
    if enriched:
        print(f"Re-enriched {enriched} records with league data")
    # Re-classify all non-Betfair records with improved logic (cross-country, youth, tier ranking)
    fixed = reenrich_leagues(force_all=True)
    if fixed:
        print(f"Fixed league classification for {fixed} CSV/PDF records")
    # Force re-classify CSV/PDF records (catches newly added TEAM_MAP entries etc.).
    # Betfair records keep their sport as set from Betfair's own EVENT_TYPE.
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE bets SET sport = NULL WHERE source != 'betfair'")
    conn.commit()
    conn.close()
    classified = migrate_sport_column()
    if classified:
        print(f"Classified sport for {classified} records")
    enriched_hr = reenrich_horse_racing()
    if enriched_hr:
        print(f"Enriched track/country for {enriched_hr} horse racing records")
    sport_fixed, cat_fixed = reenrich_football_bet_categories()
    if sport_fixed or cat_fixed:
        print(f"{sport_fixed} sport labels fixed, {cat_fixed} bet_category values cleared")
    records = db_load_all()
    data_store['data'] = records
    data_store['leagues'] = extract_leagues(records)
    data_store['markets'] = extract_markets(records)
    print(f"Loaded {len(records)} records, {len(data_store['leagues'])} leagues, {len(data_store['markets'])} markets detected")
    # Import strategy spreadsheets (Betsoccer*.xlsx). Errors logged, never fatal.
    try:
        strat_summary = import_all_strategies()
        for s in strat_summary:
            if s.get('error'):
                print(f"Strategy import: {s['file']} -> {s['error']}")
            else:
                print(f"Strategy import: {s['file']} -> {s['strategy']} ({s['imported']} rows)")
    except Exception as e:
        print(f"Strategy import failed: {e}")

initialize_app()

if __name__ == '__main__':
    # Use watchdog reloader rather than the default stat-poller — the
    # stat-poller is unreliable on Windows and can kill the worker mid-request
    # during long-running endpoints (e.g. strategies reimport), leaving the
    # port half-open and the server wedged. Falls back to the stat-poller
    # automatically if watchdog isn't installed.
    app.run(debug=True, port=5000, use_reloader=False)
