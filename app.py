"""
PDF Tabellenscraper - Web Application
Diese Anwendung lädt PDF-Tabellen herunter, filtert/sortiert sie und extrahiert Informationen von verlinkten Websites.

Installation:
pip install streamlit pandas pdfplumber requests beautifulsoup4 lxml ddgs

Anwendung starten:
streamlit run app.py
"""

import streamlit as st
import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse, quote, parse_qs
import io
import urllib.parse as up
from typing import List, Dict, Optional, Tuple
import time

# =============================================================================
# HILFSFUNKTIONEN (MÜSSEN VOR DEM HAUPTCODE STEHEN!)
# =============================================================================

GENERAL_EMAIL_PROVIDERS = [
    'gmx.ch', 'gmx.com', 'gmx.net', 'gmx.li', 'bluewin.ch', 'sky.ch', 'swissonline.ch',
    'sunrise.ch', 'bluewin.com', 'gmail.com', 'googlemail.com', 'hotmail.com',
    'hotmail.de', 'hotmail.fr', 'hotmail.co.uk', 'outlook.com', 'outlook.de',
    'outlook.fr', 'outlook.co.uk', 'live.com', 'msn.com', 'yahoo.com', 'yahoo.de',
    'yahoo.fr', 'yahoo.co.uk', 'ymail.com', 'icloud.com', 'me.com', 'mac.com',
    'protonmail.ch', 'protonmail.com', 'proton.me', 'web.de', 'freenet.de',
    't-online.de', 'aol.com', 'aol.de', 'aol.fr', 'mail.com', 'email.com',
    'zoho.com', 'yandex.com', 'yandex.ru', 'fastmail.com', 'wanadoo.fr', 'orange.fr',
    'wanadoo.com', 'laposte.net', 'sfr.fr', 'neuf.fr', 'cegetel.fr', 'free.fr',
    'bbox.fr', 'bouygtelecom.fr', 'libero.it', 'virgilio.it', 'alice.it', 'tin.it',
    'tiscali.it', 'tiscali.ch', 'tiscalinet.ch', 'telefonica.net', 'terra.es',
    'terra.com.br', 'ziggo.nl', 'kpnmail.nl', 'planet.nl', 'telfort.nl', 'online.no',
    'telia.com', 'telia.no', 'seznam.cz', 'atlas.cz', 'gmx.at', 'chello.at',
    'aon.at', 'besenova.sk'
]

PORTAL_REDIRECT_DOMAINS = [
    'orange.fr', 'wanadoo.fr', 'gmx.ch', 'gmx.net', 'gmx.com', 'gmx.li',
    'bluewin.ch', 'gmail.com', 'googlemail.com', 'hotmail.com', 'hotmail.fr',
    'outlook.com', 'live.com', 'msn.com', 'yahoo.com', 'yahoo.fr', 'yahoo.de',
    'icloud.com', 'me.com', 'web.de', 'freenet.de', 't-online.de',
    'google.com', 'google.ch', 'bing.com', 'facebook.com', 'instagram.com',
    'linkedin.com', 'wikipedia.org', 'aol.com', 'aol.de', 'aol.fr', 'orange.com',
    'portal.ch', 'login.ch', 'account.ch'
]

# Kanonische Therapie-Begriffe: Erkennungsmuster -> sauberer Ausgabe-Name
# (Regex-Muster klein geschrieben; Ausgabe so, wie sie in der Tabelle stehen soll)
THERAPY_TERMS = [
    (r'traditionelle\s+chinesische\s+medizin|\btcm\b', 'Traditionelle Chinesische Medizin (TCM)'),
    (r'akupunktur', 'Akupunktur'),
    (r'tuina', 'Tuina-Massage'),
    (r'shiatsu', 'Shiatsu'),
    (r'moxibustion|moxa-behandlung|\bmoxa\b', 'Moxibustion (Moxa)'),
    (r'schröpfglas|schröpfen|schröpfglas', 'Schröpfen'),
    (r'kräuterkunde|kräutertherapie|chinesische\s+kräuter|phytotherapie', 'Kräutertherapie / Phytotherapie'),
    (r'ernährungsberatung|ernährungslehre|diätetik', 'Ernährungsberatung / Diätetik'),
    (r'fünf\s+elemente|5\s+elemente|fünf\s+transformationen', 'Fünf-Elemente-Lehre'),
    (r'qi\s+gong', 'Qi Gong'),
    (r'tai\s+chi|taiji', 'Tai Chi'),
    (r'meditation|achtsamkeit', 'Meditation / Achtsamkeit'),
    (r'massage', 'Massage'),
    (r'fußreflexzonen|fussreflexzonen', 'Fußreflexzonenmassage'),
    (r'reflexzonen', 'Reflexzonentherapie'),
    (r'chiropraktik|chiropraktik', 'Chiropraktik'),
    (r'osteopathie', 'Osteopathie'),
    (r'physiotherapie', 'Physiotherapie'),
    (r'manuelle\s+therapie', 'Manuelle Therapie'),
    (r'aromatherapie|ätherische\s+öle', 'Aromatherapie'),
    (r'homöopathie', 'Homöopathie'),
    (r'naturheilkunde|naturheilverfahren', 'Naturheilkunde'),
    (r'cupping', 'Cupping'),
    (r'guasha|gua\s+sha', 'Gua Sha'),
    (r'qigong', 'Qi Gong'),
    (r'meridian', 'Meridian-Therapie'),
    (r'energiearbeit', 'Energiearbeit'),
    (r'意向führungs|hypnose', 'Hypnose'),
    (r'autogenes\s+training', 'Autogenes Training'),
    (r'progressive\s+muskels?entspannung|progressive\s+relaxation', 'Progressive Muskelentspannung'),
    (r'yoga', 'Yoga'),
    (r'pilates', 'Pilates'),
    (r'wickel|auflagen', 'Wickel & Auflagen'),
    (r'blutegel', 'Blutegeltherapie'),
    (r'earcandle|ohrenkerze|ohrenkerzen', 'Ohrenkerzen-Behandlung'),
    (r'kopfhautmassage|kopfmassage', 'Kopfmassage'),
    (r'firmenmassage|busines massage|büromassage', 'Firmenmassage'),
    (r'baby(qi gong)?massage|babymassage', 'Babymassage'),
    (r'pönkt|penkt|wirbelsäulen', 'Wirbelsäulentherapie'),
    (r'dorn-therapie|dorntherapie|dorn-methode', 'Dorn-Therapie'),
    (r'breuss', 'Breuss-Massage'),
    (r'grave|gravida|schwangeren(yoga|qigong|massage)?', 'Angebote für Schwangere'),
    (r'burn-?out|burnout|stressmanagement|stressbewältigung', 'Stressmanagement / Burnout-Begleitung'),
    (r'schlafstörungen', 'Begleitung bei Schlafstörungen'),
    (r'migräne', 'Behandlung von Migräne'),
    (r'allergien?', 'Behandlung von Allergien'),
    (r'verdauungs(störungen)?', 'Behandlung von Verdauungsstörungen'),
    (r'rücken(schmerzen)?', 'Behandlung von Rückenschmerzen'),
    (r'gelenks?schmerzen|arthrose', 'Behandlung von Gelenkschmerzen'),
    (r'sportverletzungen?|sporttherapie', 'Sportverletzungen / Sporttherapie'),
    (r'puerperal|wochenbett', 'Wochenbettbegleitung'),
]

def is_general_provider(domain: str) -> bool:
    domain = domain.lower().strip()
    return domain in GENERAL_EMAIL_PROVIDERS

def is_portal_domain(domain: str) -> bool:
    domain = domain.lower().strip()
    domain_clean = domain.replace('www.', '')
    return domain_clean in PORTAL_REDIRECT_DOMAINS or domain in PORTAL_REDIRECT_DOMAINS

def extract_domain_from_email(email: str) -> Optional[str]:
    try:
        if '@' not in email:
            return None
        domain = email.split('@')[1].strip()
        domain = domain.lower()
        if not domain or '.' not in domain:
            return None
        if is_general_provider(domain):
            return None
        if is_portal_domain(domain):
            return None
        return f"https://{domain}"
    except Exception:
        return None

def search_for_homepage(query: str, method: str, serpapi_key: str = "", restrict_to_ch: bool = True) -> Optional[str]:
    try:
        if "DuckDuckGo" in method:
            return search_ddgs_library(query, restrict_to_ch)
        else:
            return search_serpapi(query, serpapi_key, restrict_to_ch)
    except Exception:
        return None

def search_ddgs_library(query: str, restrict_to_ch: bool = True) -> Optional[str]:
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return None

    excluded_domains = ['local.ch', 'search.ch', 'yellow.local.ch', 'facebook.com',
                        'linkedin.com', 'twitter.com', 'instagram.com', 'youtube.com',
                        'wikipedia.org', 'doctorfmh.ch', 'reddit.com', 'tripadvisor.com',
                        'buch.ch', 'jameda.de', 'docdirekt.ch', 'gmx.ch', 'bluewin.ch',
                        'gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com',
                        'praxisfinder.ch', 'therapeuten.ch', 'medizinportal.ch',
                        'wanadoo.fr', 'orange.fr', 'google.com']

    try:
        with DDGS() as ddgs:
            if restrict_to_ch:
                enhanced_query = f"{query} site:.ch"
                results = list(ddgs.text(enhanced_query, max_results=20))
            else:
                results = list(ddgs.text(query, max_results=20))

        for res in results:
            link = res.get('href', '') or res.get('link', '')
            if not link:
                continue
            domain = urlparse(link).netloc.lower()
            title = (res.get('title', '') or res.get('headline', '')).lower()
            if any(excl in domain for excl in excluded_domains):
                continue
            if is_portal_domain(domain):
                continue
            if '.ch' in domain:
                dir_keywords = ['verzeichnis', 'liste', 'finder', 'portal', 'anbieter', 'übersicht', 'directory', 'praxisfinder', 'therapeuten', 'suche']
                if any(kw in title for kw in dir_keywords) or any(kw in domain for kw in dir_keywords):
                    continue
                if len(link) > 150:
                    continue
                return link
        return None
    except Exception:
        return None

def search_serpapi(query: str, api_key: str, restrict_to_ch: bool = True) -> Optional[str]:
    if not api_key:
        return None
    url = "https://serpapi.com/search"
    params = {'engine': 'google', 'q': query, 'api_key': api_key, 'num': 10, 'gl': 'ch'}
    if restrict_to_ch:
        params['site_search'] = '.ch'
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        excluded_domains = ['local.ch', 'search.ch', 'facebook.com', 'linkedin.com',
                            'wikipedia.org', 'doctorfmh.ch', 'tripadvisor.com', 'jameda.de',
                            'praxisfinder.ch', 'therapeuten.ch', 'wanadoo.fr', 'orange.fr', 'google.com', 'gmx.ch']
        for res in data.get('organic_results', []):
            link = res.get('link', '')
            domain = urlparse(link).netloc.lower()
            if any(excl in domain for excl in excluded_domains):
                continue
            if is_portal_domain(domain):
                continue
            if '.ch' in domain:
                return link
        return None
    except Exception:
        return None

def extract_emails(text: str) -> List[str]:
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, text)
    return list(set(emails))

def extract_site_information(url: str, info_types: List[str]) -> Dict[str, Optional[str]]:
    result = {}
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')

        if 'Name_Website' in info_types:
            title_tag = soup.find('title')
            h1_tag = soup.find('h1')
            result['Name_Website'] = title_tag.get_text().strip() if title_tag else (h1_tag.get_text().strip() if h1_tag else 'Nicht gefunden')

        if 'Mailadresse' in info_types:
            emails = extract_emails(response.text)
            result['Mailadresse'] = '; '.join(emails[:3]) if emails else 'Keine gefunden'

        if 'Telefon' in info_types:
            phones = extract_phone_numbers(response.text)
            result['Telefon'] = '; '.join(phones[:3]) if phones else 'Keine gefunden'

        if 'Adresse' in info_types:
            addresses = extract_addresses(soup, response.text)
            result['Adresse'] = addresses[:2] if addresses else 'Keine gefunden'

        if 'Über uns' in info_types:
            about_text = extract_about_section(soup)
            result['Über uns'] = about_text[:200] + '...' if about_text else 'Nicht gefunden'

        if 'Dienstleistungen' in info_types:
            services = extract_services(soup)
            result['Dienstleistungen'] = '; '.join(services) if services else 'Keine gefunden'
            result['Anzahl_Dienstleistungen'] = len(services) if services else 0

    except requests.exceptions.RequestException as e:
        result['Dienstleistungen'] = 'Keine gefunden'
        result['Anzahl_Dienstleistungen'] = 0
    return result

def extract_phone_numbers(text: str) -> List[str]:
    pattern = r'(?:\+\d{2}|0)\s*\(?[0-9]{2,5}\)?[\s.\-/][0-9\s.\-]{6,}'
    phones = re.findall(pattern, text)
    cleaned = [p.strip() for p in phones if len(re.sub(r'\D', '', p)) >= 9]
    return list(set(cleaned))[:5]

def extract_addresses(soup: BeautifulSoup, text: str) -> List[str]:
    addresses = []
    contact_sections = soup.find_all(['footer', 'address']) + soup.find_all(class_=re.compile(r'(kontakt|adresse|contact|footer)', re.I))
    for section in contact_sections[:3]:
        addr_text = section.get_text(separator='\n', strip=True)[:150]
        if addr_text and len(addr_text) > 20:
            addresses.append(addr_text)
    return addresses

def extract_about_section(soup: BeautifulSoup) -> str:
    about_keywords = ['über uns', 'about us', 'unternehmen', 'firma', 'praxis', 'praxisportrait']
    for tag in soup.find_all(['p', 'div']):
        classes = ' '.join(tag.get('class', [])).lower()
        if any(kw in classes for kw in about_keywords):
            text = tag.get_text(strip=True)
            if len(text) > 50:
                return text
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if len(text) > 100:
            return text
    return ''

def _looks_complete(item: str) -> bool:
    """Prüft, ob ein Eintrag wie ein vollständiger (nicht abgeschnittener) Text aussieht."""
    item = item.strip()
    # Verwirft Items, die mit Komma, Semikolon oder Bindestrich enden (typisch für Abbrüche)
    if item.endswith((',', ';', '-', '/', ':')):
        return False
    # Verwirft Items mit nur 1-2 Buchstaben
    letters = re.sub(r'[^a-zA-ZäöüÄÖÜéèêàâ]', '', item)
    if len(letters) < 3:
        return False
    # Verwirft Items mit unverhältnismäßig vielen Sonderzeichen
    special = len(re.sub(r'[a-zA-ZäöüÄÖÜéèêàâ0-9\s]', '', item))
    if special > len(item) * 0.3:
        return False
    return True

def _match_therapy_terms(text: str) -> List[str]:
    """Erkennt bekannte Therapie-Begriffe im Text und gibt saubere, kanonische Namen zurück."""
    text_lower = text.lower()
    found = []
    for pattern, canonical in THERAPY_TERMS:
        if re.search(pattern, text_lower):
            if canonical not in found:
                found.append(canonical)
    return found

def extract_services(soup: BeautifulSoup) -> List[str]:
    """
    SUCHT NACH THERAPIEN/BEHANDLUNGEN auf der Website.
    Priorität: Kanonische Begriffe aus THERAPY_TERMS statt abgehackter Fragmente.
    """
    services = []

    def clean(text: str) -> str:
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) < 3:
            return ''
        junk = ['cookie', 'datenschutz', 'impressum', 'login', 'anmelden', 'mehr erfahren',
                'weiterlesen', 'menu', 'navigation', 'home', 'kontakt aufnehmen',
                'allgemeine geschäftsbedingungen', 'agb', 'haftung', 'urheberrecht']
        if text.lower() in junk:
            return ''
        return text

    therapy_headings = ['therapi', 'behandlung', 'leistung', 'angebot', 'service',
                        'methode', 'schwerpunkt', 'indikation', 'behandlungsangebot',
                        'behandlungsformen', 'therapieangebot', 'kurse', 'kursangebot']

    # === STRATEGIE 1: Überschriften wie "Unsere Therapien" → Inhalte darunter ===
    for heading in soup.find_all(['h2', 'h3', 'h4']):
        heading_text = heading.get_text().lower()
        if any(pat in heading_text for pat in therapy_headings):
            for sibling in heading.next_siblings:
                if hasattr(sibling, 'name') and sibling.name in ['ul', 'ol']:
                    for li in sibling.find_all('li'):
                        item = clean(li.get_text(strip=True))
                        if item and _looks_complete(item) and 3 < len(item) < 150:
                            if item.lower() not in [s.lower() for s in services]:
                                services.append(item)
                    break
                elif hasattr(sibling, 'name') and sibling.name in ['p', 'div']:
                    text = clean(sibling.get_text(strip=True))
                    if text and len(text) < 300 and _looks_complete(text):
                        if text.lower() not in [s.lower() for s in services]:
                            services.append(text)
                    break

    # === STRATEGIE 2: Container mit passenden Klassen ===
    for container in soup.find_all(['section', 'div'],
                                   class_=re.compile(r'(leistung|behandlung|angebot|service|therapie|methode|schwerpunkt|indikation)', re.I)):
        for li in container.find_all('li'):
            item = clean(li.get_text(strip=True))
            if item and _looks_complete(item) and 3 < len(item) < 150 and item.lower() not in [s.lower() for s in services]:
                services.append(item)

        for heading in container.find_all(['h3', 'h4']):
            item = clean(heading.get_text(strip=True))
            if item and _looks_complete(item) and 3 < len(item) < 80 and item.lower() not in [s.lower() for s in services]:
                services.append(item)

    # === STRATEGIE 3: Ganzseitige Textanalyse mit kanonischen Begriffen ===
    # Statt Fragmente zu schneiden, werden ganze Absätze/Sätze gelesen und die
    # ERKANNTEN Therapien als sauberer, kanonischer Name zurückgegeben.
    page_text = soup.get_text(separator=' ', strip=True)
    detected_terms = _match_therapy_terms(page_text)
    for term in detected_terms:
        if term.lower() not in [s.lower() for s in services]:
            services.append(term)

    # Zusätzlich: Ganze Sätze mit Therapie-Erwähnungen (lesbar, nicht abgeschnitten)
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if 30 < len(text) < 400:
            # Satzweise zerlegen (nie mitten im Satz abschneiden!)
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if 20 < len(sentence) < 250 and _match_therapy_terms(sentence):
                    if _looks_complete(sentence) and sentence.lower() not in [s.lower() for s in services]:
                        services.append(sentence)

    # === STRATEGIE 4: Service-Listen (kurze Bullet-Items) ===
    for lst in soup.find_all(['ul', 'ol']):
        count = len(lst.find_all('li'))
        if 3 <= count <= 30:
            has_therapy_class = re.search(r'(leistung|behandlung|angebot|service|therapie)',
                                          ' '.join(lst.get('class', []) + [lst.get('id', '') or '']), re.I)
            if has_therapy_class:
                for li in lst.find_all('li'):
                    item = clean(li.get_text(strip=True))
                    if item and _looks_complete(item) and 3 < len(item) < 100 and item.lower() not in [s.lower() for s in services]:
                        services.append(item)

    # Deduplizieren und auf 30 begrenzen
    unique = []
    seen = set()
    for s in services:
        key = s.lower().strip()
        if key not in seen and len(key) > 3:
            seen.add(key)
            unique.append(s)
    return unique[:30]

# =============================================================================
# HAUPTANWENDUNG
# =============================================================================

st.set_page_config(page_title="PDF Tabellenscraper", page_icon="📊", layout="wide")

st.title("📄 PDF Tabellenscraper & Informations-Extraktor")
st.markdown("""
Diese Web-Anwendung:
1. Lädt eine PDF-Tabelle von einer URL herunter (alle Seiten werden zusammengeführt)
2. Filtert und sortiert die Tabelle nach ausgewählten Spalten
3. Sucht **automatisch** nach Homepages (E-Mail-Domain → URL → Websuche)
4. Extrahiert **Therapien/Behandlungen** von den gefundenen Homepages
5. Exportiert alle gesammelten Informationen als CSV
""")

# --- SCHRITT 1: PDF DOWNLOAD UND PARSING ---
st.header("Schritt 1: PDF-Tabelle herunterladen")

pdf_url = st.text_input("URL zur PDF-Tabelle eingeben:", placeholder="https://beispiel.de/tabelle.pdf")

if st.button("PDF laden"):
    if not pdf_url:
        st.error("Bitte gib eine PDF-URL ein.")
    else:
        try:
            with st.spinner("PDF wird heruntergeladen..."):
                response = requests.get(pdf_url, timeout=30)
                response.raise_for_status()

            with st.spinner("PDF wird geparst..."):
                with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                    all_tables = []
                    for i, page in enumerate(pdf.pages):
                        extracted_tables = page.extract_tables()
                        for j, table in enumerate(extracted_tables):
                            if table and len(table) > 0:
                                all_tables.append({'page': i + 1, 'table_index': j + 1, 'data': table})

            if all_tables:
                st.success(f"{len(all_tables)} Tabelle(n) auf {all_tables[-1]['page']} Seite(n) gefunden.")

                merge_mode = st.radio(
                    "Wie sollen die Tabellen verarbeitet werden?",
                    ["Alle Seiten zu EINER Tabelle zusammenführen (empfohlen)", "Nur eine einzelne Tabelle auswählen"],
                    key="merge_mode"
                )

                if merge_mode.startswith("Alle Seiten"):
                    header_row = all_tables[0]['data'][0]
                    seen = {}
                    clean_header = []
                    for col in header_row:
                        col = str(col).strip() if col else "Unbenannt"
                        if col in seen:
                            seen[col] += 1
                            clean_header.append(f"{col}_{seen[col]}")
                        else:
                            seen[col] = 0
                            clean_header.append(col)

                    all_rows = []
                    header_strs = {str(h).strip() for h in clean_header}
                    for t in all_tables:
                        for row in t['data']:
                            row_clean = [str(c).strip() if c is not None else "" for c in row]
                            if set(filter(None, row_clean)) and set(filter(None, row_clean)).issubset(header_strs):
                                continue
                            if not any(row_clean):
                                continue
                            all_rows.append(row_clean)

                    n_cols = len(clean_header)
                    fixed_rows = []
                    for row in all_rows:
                        if len(row) < n_cols:
                            row = row + [""] * (n_cols - len(row))
                        elif len(row) > n_cols:
                            row = row[:n_cols]
                        fixed_rows.append(row)

                    df = pd.DataFrame(fixed_rows, columns=clean_header)
                    df = df.reset_index(drop=True)

                    possible_email_cols = []
                    possible_url_cols = []
                    possible_name_cols = []
                    possible_vorname_cols = []
                    possible_location_cols = []

                    for col in df.columns:
                        col_lower = col.lower()
                        if any(kw in col_lower for kw in ['email', 'mail', 'e-mail', 'e mail']):
                            possible_email_cols.append(col)
                        if any(kw in col_lower for kw in ['homepage', 'website', 'url', 'webseite', 'domain']):
                            possible_url_cols.append(col)
                        if 'vorname' in col_lower or 'vor name' in col_lower:
                            possible_vorname_cols.append(col)
                        elif any(kw in col_lower for kw in ['name', 'praxis', 'arzt', 'mediziner', 'therapeut']):
                            possible_name_cols.append(col)
                        if any(kw in col_lower for kw in ['ort', 'stadt', 'standort', 'kanton', 'gemein']):
                            possible_location_cols.append(col)

                    if possible_email_cols:
                        st.info(f"📧 {len(possible_email_cols)} Spalte(n) mit E-Mail-Inhalten gefunden: {', '.join(possible_email_cols)}")

                    st.info(f"ℹ️ Zusammengeführt: {len(df)} Datenzeilen aus {len(all_tables)} Tabellensegmenten")
                else:
                    labels = [f"Tabelle {t['table_index']} auf Seite {t['page']} ({len(t['data'])-1} Zeilen)" for t in all_tables]
                    chosen = st.selectbox("Wähle die Tabelle zum Verarbeiten:", labels, key="table_select")
                    sel_idx = labels.index(chosen)
                    selected_table_data = all_tables[sel_idx]['data']
                    df = pd.DataFrame(selected_table_data[1:], columns=selected_table_data[0])
                    df = df.reset_index(drop=True)

                    possible_email_cols = []
                    possible_url_cols = []
                    possible_name_cols = []
                    possible_vorname_cols = []
                    possible_location_cols = []

                    for col in df.columns:
                        col_lower = col.lower()
                        if any(kw in col_lower for kw in ['email', 'mail', 'e-mail', 'e mail']):
                            possible_email_cols.append(col)
                        if any(kw in col_lower for kw in ['homepage', 'website', 'url', 'webseite', 'domain']):
                            possible_url_cols.append(col)
                        if 'vorname' in col_lower or 'vor name' in col_lower:
                            possible_vorname_cols.append(col)
                        elif any(kw in col_lower for kw in ['name', 'praxis', 'arzt', 'mediziner', 'therapeut']):
                            possible_name_cols.append(col)
                        if any(kw in col_lower for kw in ['ort', 'stadt', 'standort', 'kanton', 'gemein']):
                            possible_location_cols.append(col)

                st.dataframe(df.head(15), use_container_width=True)
                st.caption(f"Gesamte Zeilen: {len(df)} | Spalten: {len(df.columns)}")

                st.session_state['pdf_df'] = df
                st.session_state['df_columns'] = list(df.columns)
                st.session_state['possible_email_cols'] = possible_email_cols
                st.session_state['possible_url_cols'] = possible_url_cols
                st.session_state['possible_name_cols'] = possible_name_cols
                st.session_state['possible_vorname_cols'] = possible_vorname_cols
                st.session_state['possible_location_cols'] = possible_location_cols
                st.session_state['pdf_loaded'] = True
                st.session_state['sorted'] = False
                st.session_state['scraped_results'] = None
            else:
                st.warning("Keine Tabellen im PDF gefunden.")
        except Exception as e:
            st.error(f"Fehler beim Laden des PDFs: {str(e)}")

# --- SCHRITT 2: FILTERN UND SORTIEREN ---
if st.session_state.get('pdf_loaded', False):
    st.header("Schritt 2: Tabelle filtern und sortieren")

    available_columns = st.session_state['df_columns']
    df = st.session_state['pdf_df']

    st.subheader("🔎 Filter")

    use_filter = st.checkbox("Nur Zeilen anzeigen, die bestimmte Einträge enthalten", value=True)

    filtered_df = df.copy()
    ws_filter_col1 = None
    ws_filter_text1 = None

    if use_filter:
        filter_col1 = st.selectbox("Filter 1 – Spalte:", available_columns, key="filter_col1")
        filter_text1 = st.text_input("Filter 1 – Welcher Eintrag soll enthalten sein?", key="filter_text1")

        if filter_text1:
            mask1 = filtered_df[filter_col1].astype(str).str.contains(filter_text1, case=False, na=False)
            filtered_df = filtered_df[mask1]
            st.caption(f"Filter 1: {mask1.sum()} Zeilen gefunden")

        add_second_filter = st.checkbox("Zweiten Filter hinzufügen (beide müssen zutreffen)")

        if add_second_filter:
            filter_col2 = st.selectbox("Filter 2 – Spalte:", available_columns, key="filter_col2")
            filter_text2 = st.text_input("Filter 2 – Welcher Eintrag soll enthalten sein?", key="filter_text2")
            if filter_text2:
                mask2 = filtered_df[filter_col2].astype(str).str.contains(filter_text2, case=False, na=False)
                filtered_df = filtered_df[mask2]

        if filter_text1 or (add_second_filter and st.session_state.get("filter_text2")):
            st.info(f"✅ {len(filtered_df)} von {len(df)} Zeilen entsprechen den Filtern.")

        ws_filter_col1 = filter_col1
        ws_filter_text1 = filter_text1
    else:
        st.caption("Kein Filter aktiv – alle Zeilen werden verwendet.")

    st.subheader("↕️ Sortierung")

    sort_col1 = st.selectbox("Primärsortierung (Spalte)", available_columns, key="sort_col1")
    sort_order1 = st.radio("Sortierreihenfolge", ["Aufsteigend (A-Z)", "Absteigend (Z-A)"], index=0, key="sort_order1")

    add_second_sort = st.checkbox("Zweite Sortierspalte hinzufügen")
    sort_col2 = None

    if add_second_sort:
        sort_col2 = st.selectbox("Sekundärsortierung (Spalte)", available_columns, key="sort_col2")
        sort_order2 = st.radio("Sortierreihenfolge (2. Spalte)", ["Aufsteigend (A-Z)", "Absteigend (Z-A)"], index=0, key="sort_order2")

    if st.button("Filter und Sortierung anwenden"):
        result_df = filtered_df.copy()
        ascending1 = sort_order1 == "Aufsteigend (A-Z)"
        if add_second_sort and sort_col2:
            ascending2 = sort_order2 == "Aufsteigend (A-Z)"
            result_df = result_df.sort_values(by=[sort_col1, sort_col2], ascending=[ascending1, ascending2])
        else:
            result_df = result_df.sort_values(by=sort_col1, ascending=ascending1)

        result_df = result_df.reset_index(drop=True)
        st.session_state['filtered_df'] = result_df
        st.session_state['sorted'] = True
        st.session_state['ws_filter_col1'] = ws_filter_col1
        st.session_state['ws_filter_text1'] = ws_filter_text1
        st.success(f"Tabelle verarbeitet! {len(result_df)} Zeilen bereit.")

    if st.session_state.get('sorted', False) and 'filtered_df' in st.session_state:
        st.subheader("Vorschau der gefilterten & sortierten Tabelle")
        st.dataframe(st.session_state['filtered_df'], use_container_width=True)

        csv_filtered = st.session_state['filtered_df'].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Gefilterte Tabelle als CSV herunterladen",
            data=csv_filtered,
            file_name='gefilterte_tabelle.csv',
            mime='text/csv',
            key="download_filtered"
        )

# --- SCHRITT 2B: HOMEPAGES AUTOMATISCH FINDEN ---
if st.session_state.get('sorted', False) and 'filtered_df' in st.session_state:
    st.header("Schritt 2b: Homepages automatisch finden 🔍")

    available_columns = st.session_state['df_columns']
    work_df = st.session_state['filtered_df'].copy()

    st.markdown("""
    **Die App sucht jetzt in dieser Reihenfolge:**
    1. 📧 **E-Mail-Adressen** → Domain extrahieren (nur bei echten Praxis-Domains!)
    2. 🔗 **Vorhandene URLs** → Direkt verwenden
    3. 🌐 **Websuche** → Name + Ort + **Filter 1** (nur .ch Domains)
    """)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        email_options = ["— Keine —"] + st.session_state.get('possible_email_cols', [])
        email_default_index = 1 if len(st.session_state.get('possible_email_cols', [])) == 1 else 0
        email_col = st.selectbox("E-Mail-Spalte:", email_options, index=email_default_index, key="email_col")

    with col2:
        url_options = ["— Keine —"] + st.session_state.get('possible_url_cols', [])
        url_default_index = 1 if len(st.session_state.get('possible_url_cols', [])) == 1 else 0
        url_col = st.selectbox("URL/Homepage-Spalte:", url_options, index=url_default_index, key="url_col")

    with col3:
        name_options = st.session_state.get('possible_name_cols', available_columns)
        name_col = st.selectbox("Name-Spalte:", name_options, index=0 if name_options else 0, key="name_col")

    with col4:
        location_options = ["— Keine —"] + st.session_state.get('possible_location_cols', [])
        location_default_index = 1 if len(st.session_state.get('possible_location_cols', [])) == 1 else 0
        location_col = st.selectbox("Ort-Spalte:", location_options, index=location_default_index, key="location_col")

    st.divider()
    st.subheader("🔍 Websuche-Einstellungen (wird nur benutzt, falls keine E-Mail/URL vorhanden)")

    ws_filter_text1 = st.session_state.get('ws_filter_text1')
    if ws_filter_text1:
        st.success(f"💡 Filter 1 wird in die Websuche einbezogen: **„{ws_filter_text1}“**")
    else:
        st.caption("ℹ️ Es ist kein Filter 1 gesetzt – die Suche nutzt nur Name + Ort.")

    st.info("**Websuche-Bestandteile:** Name + Ort + **Filter 1-Eintrag** + schweiz + praxis | Nur .ch Domains")

    search_method = st.radio(
        "Welche Websuche soll verwendet werden?",
        ["DuckDuckGo via ddgs (kostenlos, .ch-Fokus)", "SerpApi Google Search (bessere Ergebnisse, braucht API-Key)"],
        key="search_method_step2b"
    )

    serapi_key = ""
    if "SerpApi" in search_method:
        serapi_key = st.text_input("SerpApi API-Key eingeben:", type="password", help="API-Key unter https://serpapi.com/")

    total_rows = len(work_df)
    has_practice_email = 0
    has_url = 0
    needs_search = 0
    has_generic_email = 0

    for idx, row in work_df.iterrows():
        if email_col != "— Keine —":
            email_val = str(row[email_col]).strip()
            if email_val and '@' in email_val:
                domain = extract_domain_from_email(email_val)
                if domain:
                    has_practice_email += 1
                    continue
                else:
                    has_generic_email += 1
                    continue
        if url_col != "— Keine —":
            url_val = str(row[url_col]).strip()
            if url_val and url_val.startswith('http'):
                has_url += 1
                continue
        needs_search += 1

    st.info(f"**Analyse Ihrer Tabelle:** Praxis-E-Mail: **{has_practice_email}** | Allgemeine E-Mail: **{has_generic_email}** | URL: **{has_url}** | Websuche nötig: **{needs_search}/{total_rows}**")

    max_search_rows = st.slider("Maximale Anzahl Websuchen (nur Zeilen ohne E-Mail/URL):", 1, needs_search + has_generic_email, min(needs_search + has_generic_email, 20))

    if st.button("Homepages automatisch finden 🚀"):
        progress_ws = st.progress(0)
        status_ws = st.empty()
        detail_log = []
        search_done = 0
        filter_term = st.session_state.get('ws_filter_text1')

        for idx, row in work_df.head(total_rows).iterrows():
            homepage_found = None
            method_used = None
            query = ""

            if email_col != "— Keine —":
                email_val = str(row[email_col]).strip()
                if email_val and '@' in email_val:
                    domain = extract_domain_from_email(email_val)
                    if domain:
                        homepage_found = domain
                        method_used = "E-Mail Domain"

            if not homepage_found and url_col != "— Keine —":
                url_val = str(row[url_col]).strip()
                if url_val and url_val.lower().startswith(('http://', 'https://')):
                    url_domain = urlparse(url_val).netloc.lower()
                    if not is_portal_domain(url_domain):
                        homepage_found = url_val
                        method_used = "Bestehende URL"

            if not homepage_found:
                if search_done >= max_search_rows:
                    method_used = "Max WebSearch erreicht"
                else:
                    name = str(row[name_col]).strip() if name_col != "— Keine —" else ""
                    location = str(row[location_col]).strip() if location_col != "— Keine —" else ""
                    query_parts = []
                    if name:
                        query_parts.append(name)
                    if location:
                        query_parts.append(location)
                    if filter_term:
                        query_parts.append(filter_term)
                    query_parts.extend(["schweiz", "praxis"])
                    query = " ".join(query_parts)
                    homepage_found = search_for_homepage(query, search_method, serapi_key, restrict_to_ch=True)
                    search_done += 1
                    method_used = "Websuche"
                    progress_ws.progress(search_done / max_search_rows if max_search_rows > 0 else 1.0)

            if homepage_found:
                work_df.at[idx, 'Gefundene_Homepage'] = homepage_found
                detail_log.append(f"✅ {row[name_col]} → {homepage_found} ({method_used})")
            else:
                work_df.at[idx, 'Gefundene_Homepage'] = "Nicht gefunden"
                detail_log.append(f"❌ {row[name_col]} → Nicht gefunden | Suchbegriff: {query}")

            status_ws.text(f"Bearbeitet {idx+1}/{total_rows} | Websuche {search_done}/{max_search_rows}")
            time.sleep(0.8)

        status_ws.text("Abgeschlossen! ✅")
        cols = [c for c in work_df.columns if c != 'Gefundene_Homepage'] + ['Gefundene_Homepage']
        work_df = work_df[cols]
        st.session_state['filtered_df'] = work_df
        st.session_state['websuche_completed'] = True

        found_count = (work_df['Gefundene_Homepage'] != 'Nicht gefunden').sum()
        st.info(f"✅ {found_count} von {total_rows} Homepages gefunden ({search_done} Websuchen durchgeführt)")

        with st.expander("📋 Detail-Protokoll ansehen"):
            for log_line in detail_log[:20]:
                st.text(log_line)
            if len(detail_log) > 20:
                st.caption(f"... weitere {len(detail_log) - 20} Einträge")

        st.subheader("Ergebnisse")
        show_cols = [name_col, 'Gefundene_Homepage']
        if location_col != "— Keine —":
            show_cols.insert(1, location_col)
        st.dataframe(work_df[show_cols], use_container_width=True)

    if st.session_state.get('websuche_completed'):
        st.info("💾 Die Tabelle enthält jetzt die Spalte 'Gefundene_Homepage'. Weiter mit Schritt 3!")

# --- SCHRITT 3: THERAPIEN UND INFORMATIONEN EXTRAHIEREN ---
if st.session_state.get('sorted', False) and 'filtered_df' in st.session_state:
    st.header("Schritt 3: Therapien & Angebote von Homepages extrahieren 🏥")

    work_df = st.session_state['filtered_df']
    available_columns = list(work_df.columns)

    st.markdown("""
    Die App besucht jede Homepage und extrahiert **Therapien/Behandlungen** (z. B. Akupunktur, Tuina, Kräutertherapie)
    sowie optional Mailadresse, Telefon und andere Kontaktdaten.
    Das Ergebnis erscheint in einer Tabelle mit **Name, Vorname** und den gefundenen Therapien.
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        homepage_options = ["— Keine —"] + [c for c in available_columns if 'homepage' in c.lower()]
        homepage_default = 1 if len(homepage_options) > 1 else 0
        homepage_col = st.selectbox("Spalte mit Homepage-URL:", homepage_options, index=homepage_default, key="homepage_col_extract")

    with col2:
        name_extract_options = st.session_state.get('possible_name_cols', available_columns)
        name_extract_col = st.selectbox("Name-Spalte:", name_extract_options, index=0 if name_extract_options else 0, key="name_extract_col")

    with col3:
        vorname_options = ["— Keine —"] + st.session_state.get('possible_vorname_cols', [])
        vorname_default_index = 1 if len(st.session_state.get('possible_vorname_cols', [])) == 1 else 0
        vorname_col = st.selectbox("Vorname-Spalte:", vorname_options, index=vorname_default_index, key="vorname_col_extract")

    st.divider()
    st.subheader("Welche zusätzlichen Informationen sollen extrahiert werden?")
    info_columns = st.multiselect(
        "Zusätzliche Felder (Therapien werden immer extrahiert):",
        ["Mailadresse", "Telefon", "Adresse", "Über uns", "Name_Website"],
        default=[],
        key="info_cols_extract"
    )

    st.info("""
    **Hinweis:**
    - Die Website muss öffentlich zugänglich sein
    - Manche Seiten benötigen JavaScript (dann wird die Extraktion eventuell unvollständig)
    - Die App wartet 1 Sekunde zwischen Anfragen
    - **Tipp:** Bei vielen Zeilen mehrere kleine Durchläufe machen (10–20 Zeilen)
    """)

    num_rows = len(work_df)
    max_rows = st.slider("Wie viele Zeilen verarbeiten?", 1, num_rows, min(num_rows, 10))

    if st.button("Therapien extrahieren 🚀"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        processed = 0

        for _, row in work_df.head(max_rows).iterrows():
            processed += 1
            status_text.text(f"Verarbeite Zeile {processed}/{max_rows}: {str(row[name_extract_col])[:40]}")

            homepage_value = str(row[homepage_col]).strip()
            if (not homepage_value or homepage_value == "Nicht gefunden" or
                (homepage_value.lower().startswith(('http://', 'https://')) is False and '.' not in homepage_value)):
                homepage_value = ""
            if homepage_value and not homepage_value.lower().startswith(('http://', 'https://')):
                homepage_value = f"https://{homepage_value}"

            base = {'Name': row[name_extract_col], 'Vorname': row[vorname_col] if vorname_col != "— Keine —" else ""}

            try:
                if homepage_value:
                    extracted_info = extract_site_information(homepage_value, info_columns + ['Dienstleistungen'])
                    results.append({**base, **{homepage_col: row[homepage_col]}, **extracted_info})
                else:
                    results.append({**base, homepage_col: row[homepage_col],
                                    'Dienstleistungen': 'Keine Homepage vorhanden',
                                    'Anzahl_Dienstleistungen': 0})
            except Exception:
                results.append({**base, homepage_col: row[homepage_col],
                                'Dienstleistungen': 'Fehler beim Abruf',
                                'Anzahl_Dienstleistungen': 0})

            progress_bar.progress(processed / max_rows)
            time.sleep(1)

        status_text.text("Fertig! ✅")
        results_df = pd.DataFrame(results)

        # Error-Spalte entfernen (soll nicht in der Ausgabe erscheinen)
        if 'Error' in results_df.columns:
            results_df = results_df.drop(columns=['Error'])

        st.session_state['scraped_results_df'] = results_df
        st.success(f"✅ {len(results_df)} Praxen bearbeitet")

    if st.session_state.get('scraped_results_df') is not None:
        results_df = st.session_state['scraped_results_df'].copy()

        # Sicherheitshalber Error-Spalte auch hier entfernen
        if 'Error' in results_df.columns:
            results_df = results_df.drop(columns=['Error'])

        st.subheader("📊 Ergebnistabelle")
        st.dataframe(results_df, use_container_width=True)

        csv_export = results_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Ergebnisse als CSV herunterladen",
            data=csv_export,
            file_name='therapien_ergebnisse.csv',
            mime='text/csv',
            key="download_results"
        )

        if 'Dienstleistungen' in results_df.columns:
            found_mask = (~results_df['Dienstleistungen'].isin(['Keine gefunden', 'Keine Homepage vorhanden', 'Fehler beim Abruf']))
            found = found_mask.sum()
            st.caption(f"📈 Bei **{found} von {len(results_df)}** Praxen wurden Therapien gefunden.")

        if 'Anzahl_Dienstleistungen' in results_df.columns:
            total_services = sum(int(str(x)) if str(x).isdigit() else 0 for x in results_df['Anzahl_Dienstleistungen'])
            avg_services = round(total_services / len(results_df), 1) if len(results_df) > 0 else 0
            st.caption(f"➡️ Insgesamt **{total_services}** Therapien erkannt | Durchschnittlich **{avg_services}** pro Praxis")

st.markdown("---")
st.caption("⚠️ **Rechtlicher Hinweis**: Respektiere die robots.txt der Zielseiten und vermeide zu häufige Anfragen.")
