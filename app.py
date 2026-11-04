"""
PDF Tabellenscraper - Web Application
Diese Anwendung lädt PDF-Tabellen herunter, filtert/sortiert sie und extrahiert Informationen von verlinkten Websites.

Installation:
pip install streamlit pandas pdfplumber requests beautifulsoup4 lxml

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
from typing import List, Dict, Optional
import time

# =============================================================================
# HILFSFUNKTIONEN (MÜSSEN VOR DEM HAUPTCODE STEHEN!)
# =============================================================================

def search_for_homepage(query: str, method: str, serpapi_key: str = "") -> Optional[str]:
    """Sucht im Web nach einer Homepage basierend auf dem Suchbegriff"""
    try:
        if "DuckDuckGo" in method:
            return search_duckduckgo(query)
        else:
            return search_serpapi(query, serpapi_key)
    except Exception:
        return None

def search_duckduckgo(query: str) -> Optional[str]:
    """Nutzt DuckDuckGo HTML-Suche (einfach, kostenlos)"""
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.post(url, data={'q': query}, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')

        results = soup.select('a.result__a')

        if results:
            first_link = results[0].get('href', '')

            # DuckDuckGo leitet manchmal über uddg= Parameter weiter
            if 'uddg=' in first_link:
                parsed = up.parse_qs(up.urlparse(first_link).query)
                if 'uddg' in parsed:
                    first_link = parsed['uddg'][0]

            # Verzeichnisse ausschließen
            excluded_domains = ['local.ch', 'search.ch', 'yellow.local.ch', 'facebook.com',
                                'linkedin.com', 'twitter.com', 'instagram.com', 'youtube.com',
                                'wikipedia.org', 'doctorfmh.ch']

            domain = urlparse(first_link).netloc.lower()
            if domain and not any(excl in domain for excl in excluded_domains):
                return first_link

        return None
    except Exception:
        return None

def search_serpapi(query: str, api_key: str) -> Optional[str]:
    """Nutzt SerpApi Google Search"""
    if not api_key:
        return None

    url = "https://serpapi.com/search"
    params = {
        'engine': 'google',
        'q': query,
        'api_key': api_key,
        'num': 5
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()

        excluded_domains = ['local.ch', 'search.ch', 'facebook.com', 'linkedin.com',
                            'wikipedia.org', 'doctorfmh.ch']

        for res in data.get('organic_results', []):
            link = res.get('link', '')
            domain = urlparse(link).netloc.lower()
            if domain and not any(excl in domain for excl in excluded_domains):
                return link

        return None
    except Exception:
        return None

def extract_site_information(url: str, info_types: List[str]) -> Dict[str, Optional[str]]:
    """Extrahiert verschiedene Informationen von einer Website"""
    result = {}

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')

        if 'Name' in info_types:
            title_tag = soup.find('title')
            h1_tag = soup.find('h1')
            result['Name'] = title_tag.get_text().strip() if title_tag else (h1_tag.get_text().strip() if h1_tag else 'Nicht gefunden')

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
            result['Dienstleistungen'] = '; '.join(services[:8]) if services else 'Keine gefunden'

    except requests.exceptions.RequestException as e:
        result['Error'] = f"HTTP Error: {str(e)}"

    return result

def extract_emails(text: str) -> List[str]:
    """Sucht nach E-Mail Adressen im Text"""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, text)
    return list(set(emails))

def extract_phone_numbers(text: str) -> List[str]:
    """Sucht nach Telefonnummern"""
    pattern = r'(?:\+\d{2}|0)\s*\(?[0-9]{2,5}\)?[\s.\-/][0-9\s.\-]{6,}'
    phones = re.findall(pattern, text)
    cleaned = [p.strip() for p in phones if len(re.sub(r'\D', '', p)) >= 9]
    return list(set(cleaned))[:5]

def extract_addresses(soup: BeautifulSoup, text: str) -> List[str]:
    """Versucht Adressen zu finden"""
    addresses = []

    contact_sections = soup.find_all(['footer', 'address']) + soup.find_all(class_=re.compile(r'(kontakt|adresse|contact|footer)', re.I))

    for section in contact_sections[:3]:
        addr_text = section.get_text(separator='\n', strip=True)[:150]
        if addr_text and len(addr_text) > 20:
            addresses.append(addr_text)

    return addresses

def extract_about_section(soup: BeautifulSoup) -> str:
    """Sucht nach 'Über uns' Text"""
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

def extract_services(soup: BeautifulSoup) -> List[str]:
    """Sucht nach Dienstleistungs-Listen"""
    services = []

    service_patterns = [
        'service', 'angebot', 'dienstleistung', 'leistungen', 'behandlung',
        'therapie', 'therapien', 'methoden', 'anwendung'
    ]

    for pattern in service_patterns:
        lists = soup.find_all(['ul', 'ol'], class_=re.compile(pattern, re.I))
        for lst in lists:
            for li in lst.find_all('li')[:10]:
                service_text = li.get_text(strip=True)
                if 10 < len(service_text) < 100:
                    services.append(service_text)

    for container in soup.find_all(['section', 'div'], class_=re.compile(r'(leistungen|behandlung|angebote|services)', re.I)):
        for li in container.find_all('li')[:10]:
            service_text = li.get_text(strip=True)
            if 10 < len(service_text) < 100 and service_text not in services:
                services.append(service_text)

    for heading in soup.find_all(['h2', 'h3']):
        if any(keyword in heading.get_text().lower() for keyword in ['behandlung', 'leistung', 'angebot', 'therapie', 'methoden']):
            sibling = heading.find_next(['ul', 'ol'])
            if sibling:
                for li in sibling.find_all('li')[:10]:
                    service_text = li.get_text(strip=True)
                    if 10 < len(service_text) < 100 and service_text not in services:
                        services.append(service_text)

    return services[:15]

# =============================================================================
# HAUPTANWENDUNG
# =============================================================================

# Seite konfigurieren
st.set_page_config(
    page_title="PDF Tabellenscraper",
    page_icon="📊",
    layout="wide"
)

st.title("📄 PDF Tabellenscraper & Informations-Extraktor")
st.markdown("""
Diese Web-Anwendung:
1. Lädt eine PDF-Tabelle von einer URL herunter (alle Seiten werden zusammengeführt)
2. Filtert und sortiert die Tabelle nach ausgewählten Spalten
3. Sucht im Web nach Homepages (falls keine URL vorhanden ist)
4. Extrahiert Praxis-Namen, Mailadressen, Telefon, Dienstleistungen und weitere Details
5. Exportiert alle gesammelten Informationen als CSV
""")

# --- SCHRITT 1: PDF DOWNLOAD UND PARSING ---
st.header("Schritt 1: PDF-Tabelle herunterladen")

pdf_url = st.text_input(
    "URL zur PDF-Tabelle eingeben:",
    placeholder="https://beispiel.de/tabelle.pdf"
)

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
                                all_tables.append({
                                    'page': i + 1,
                                    'table_index': j + 1,
                                    'data': table
                                })

            if all_tables:
                st.success(f"{len(all_tables)} Tabelle(n) auf {all_tables[-1]['page']} Seite(n) gefunden.")

                merge_mode = st.radio(
                    "Wie sollen die Tabellen verarbeitet werden?",
                    [
                        "Alle Seiten zu EINER Tabelle zusammenführen (empfohlen)",
                        "Nur eine einzelne Tabelle auswählen"
                    ],
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

                    st.info(f"ℹ️ Zusammengeführt: {len(df)} Datenzeilen aus {len(all_tables)} Tabellensegmenten")
                else:
                    labels = [f"Tabelle {t['table_index']} auf Seite {t['page']} ({len(t['data'])-1} Zeilen)" for t in all_tables]
                    chosen = st.selectbox("Wähle die Tabelle zum Verarbeiten:", labels, key="table_select")
                    sel_idx = labels.index(chosen)
                    selected_table_data = all_tables[sel_idx]['data']

                    df = pd.DataFrame(selected_table_data[1:], columns=selected_table_data[0])
                    df = df.reset_index(drop=True)

                st.dataframe(df.head(15), use_container_width=True)
                st.caption(f"Gesamte Zeilen: {len(df)} | Spalten: {len(df.columns)}")

                st.session_state['pdf_df'] = df
                st.session_state['df_columns'] = list(df.columns)
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

    # ===== FILTERUNG =====
    st.subheader("🔎 Filter")

    use_filter = st.checkbox("Nur Zeilen anzeigen, die bestimmte Einträge enthalten", value=True)

    filtered_df = df.copy()

    if use_filter:
        filter_col1 = st.selectbox(
            "Filter 1 – Spalte:",
            available_columns,
            key="filter_col1"
        )
        filter_text1 = st.text_input(
            "Filter 1 – Welcher Eintrag soll enthalten sein?",
            key="filter_text1"
        )
        if filter_text1:
            mask1 = filtered_df[filter_col1].astype(str).str.contains(
                filter_text1, case=False, na=False
            )
            filtered_df = filtered_df[mask1]
            st.caption(f"Filter 1: {mask1.sum()} Zeilen gefunden")

        add_second_filter = st.checkbox("Zweiten Filter hinzufügen (beide müssen zutreffen)")

        if add_second_filter:
            filter_col2 = st.selectbox(
                "Filter 2 – Spalte:",
                available_columns,
                key="filter_col2"
            )
            filter_text2 = st.text_input(
                "Filter 2 – Welcher Eintrag soll enthalten sein?",
                key="filter_text2"
            )
            if filter_text2:
                mask2 = filtered_df[filter_col2].astype(str).str.contains(
                    filter_text2, case=False, na=False
                )
                filtered_df = filtered_df[mask2]

        if filter_text1 or (add_second_filter and st.session_state.get("filter_text2")):
            st.info(f"✅ {len(filtered_df)} von {len(df)} Zeilen entsprechen den Filtern.")
    else:
        st.caption("Kein Filter aktiv – alle Zeilen werden verwendet.")

    # ===== SORTIERUNG =====
    st.subheader("↕️ Sortierung")

    sort_col1 = st.selectbox(
        "Primärsortierung (Spalte)",
        available_columns,
        key="sort_col1"
    )

    sort_order1 = st.radio(
        "Sortierreihenfolge",
        ["Aufsteigend (A-Z)", "Absteigend (Z-A)"],
        index=0,
        key="sort_order1"
    )

    add_second_sort = st.checkbox("Zweite Sortierspalte hinzufügen")
    sort_col2 = None

    if add_second_sort:
        sort_col2 = st.selectbox(
            "Sekundärsortierung (Spalte)",
            available_columns,
            key="sort_col2"
        )
        sort_order2 = st.radio(
            "Sortierreihenfolge (2. Spalte)",
            ["Aufsteigend (A-Z)", "Absteigend (Z-A)"],
            index=0,
            key="sort_order2"
        )

    if st.button("Filter und Sortierung anwenden"):
        result_df = filtered_df.copy()

        ascending1 = sort_order1 == "Aufsteigend (A-Z)"
        if add_second_sort and sort_col2:
            ascending2 = sort_order2 == "Aufsteigend (A-Z)"
            result_df = result_df.sort_values(
                by=[sort_col1, sort_col2],
                ascending=[ascending1, ascending2]
            )
        else:
            result_df = result_df.sort_values(
                by=sort_col1,
                ascending=ascending1
            )

        result_df = result_df.reset_index(drop=True)
        st.session_state['filtered_df'] = result_df
        st.session_state['sorted'] = True
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

# --- SCHRITT 2A: WEBSUCHE FÜR FEHLENDE URLS ---
if st.session_state.get('sorted', False) and 'filtered_df' in st.session_state:
    st.header("Schritt 2a: Homepages im Web suchen (optional)")

    available_columns = st.session_state['df_columns']
    work_df = st.session_state['filtered_df'].copy()

    st.markdown("""
    **Wenn deine PDF keine Homepages enthält**, kannst du hier eine Websuche durchführen lassen.
    Die App sucht nach "Praxisname + Ort" und findet mögliche Websites.
    """)

    col1, col2 = st.columns(2)

    with col1:
        name_column = st.selectbox(
            "Spalte mit Praxis/Namen:",
            available_columns,
            key="name_col_websearch"
        )

    with col2:
        location_column = st.selectbox(
            "Spalte mit Ort/Kanton (optional):",
            ["— Keine —"] + available_columns,
            key="location_col_websearch"
        )

    # API-Auswahl
    st.subheader("🔍 Suchmethode wählen")

    search_method = st.radio(
        "Welche Websuche soll verwendet werden?",
        [
            "DuckDuckGo (kostenlos, keine Registrierung)",
            "SerpApi Google Search (bessere Ergebnisse, braucht API-Key)"
        ],
        key="search_method"
    )

    serapi_key = ""
    if "SerpApi" in search_method:
        serapi_key = st.text_input(
            "SerpApi API-Key eingeben:",
            type="password",
            help="API-Key unter https://serpapi.com/ erhalten. Kostenlos bis 100 Suchen/Monat."
        )
        if not serapi_key:
            st.warning("⚠️ Ohne API-Key funktioniert SerpApi nicht. Alternativ DuckDuckGo wählen.")

    max_websearch_rows = st.slider(
        "Maximale Anzahl Zeilen websuchen:",
        1,
        len(work_df),
        min(len(work_df), 20),
        key="max_websearch"
    )

    if st.button("Websuche durchführen 🔍"):
        progress_ws = st.progress(0)
        status_ws = st.empty()

        done = 0
        for idx, row in work_df.head(max_websearch_rows).iterrows():
            done += 1
            status_ws.text(f"Suche {done}/{max_websearch_rows}: {row[name_column]}")

            name = str(row[name_column]).strip()
            location = ""

            if location_column != "— Keine —":
                location = str(row[location_column]).strip()

            # Suchbegriff bauen
            query = f"{name}"
            if location:
                query += f" {location}"

            homepage_url = search_for_homepage(query, search_method, serapi_key)

            if homepage_url:
                work_df.at[idx, 'Gesuchte_Homepage'] = homepage_url
            else:
                work_df.at[idx, 'Gesuchte_Homepage'] = "Nicht gefunden"

            progress_ws.progress(done / max_websearch_rows)
            time.sleep(2)  # Rate limiting

        status_ws.text("Websuche abgeschlossen! ✅")

        # Spalte ans Ende sortieren
        cols = [c for c in work_df.columns if c != 'Gesuchte_Homepage'] + ['Gesuchte_Homepage']
        work_df = work_df[cols]

        st.session_state['filtered_df'] = work_df
        st.session_state['websuche_completed'] = True

        found_count = (work_df['Gesuchte_Homepage'] != 'Nicht gefunden').sum()
        st.info(f"✅ {found_count} von {len(work_df)} Homepages gefunden.")

        st.subheader("Ergebnisse der Websuche")
        st.dataframe(work_df[[name_column] + (['Gesuchte_Homepage'] if 'Gesuchte_Homepage' in work_df.columns else [])], use_container_width=True)

    if st.session_state.get('websuche_completed'):
        st.info("💾 Die Tabelle enthält jetzt die Spalte 'Gesuchte_Homepage'. Weiter mit Schritt 3!")

# --- SCHRITT 3: HOMEPAGE EXTRACTION ---
if st.session_state.get('sorted', False) and 'filtered_df' in st.session_state:
    st.header("Schritt 3: Informationen von Homepages extrahieren")

    work_df = st.session_state['filtered_df']
    available_columns = list(work_df.columns)

    col1, col2 = st.columns(2)

    with col1:
        homepage_col = st.selectbox(
            "Spalte mit Homepage-URL:",
            available_columns,
            key="homepage_col_extract"
        )

    with col2:
        info_columns = st.multiselect(
            "Welche Informationen sollen extrahiert werden?",
            ["Name", "Mailadresse", "Telefon", "Adresse", "Über uns", "Dienstleistungen"],
            default=["Name", "Mailadresse", "Dienstleistungen"],
            key="info_cols_extract"
        )

    st.info("""
    **Hinweis:**
    - Die Website muss öffentlich zugänglich sein
    - Manche Seiten benötigen JavaScript (dann funktioniert dies eventuell nicht vollständig)
    - Die App wartet 1 Sekunde zwischen Anfragen
    - **Tipp:** Bei vielen Zeilen mehrere kleine Durchläufe machen (10–20 Zeilen)
    """)

    num_rows = len(work_df)
    max_rows = st.slider(
        "Wie viele Zeilen verarbeiten?",
        1,
        num_rows,
        min(num_rows, 10)
    )

    if st.button("Informationen extrahieren 🚀"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        processed = 0

        for _, row in work_df.head(max_rows).iterrows():
            processed += 1
            status_text.text(f"Verarbeite Zeile {processed}/{max_rows}")

            homepage_value = str(row[homepage_col]).strip()

            if (not homepage_value
                    or homepage_value == "Nicht gefunden"
                    or homepage_value.lower().startswith(('http://', 'https://')) is False
                    and '.' not in homepage_value):
                homepage_value = ""

            if homepage_value and not homepage_value.lower().startswith(('http://', 'https://')):
                homepage_value = f"https://{homepage_value}"

            try:
                if homepage_value:
                    extracted_info = extract_site_information(homepage_value, info_columns)
                    results.append({
                        'Zeile': processed,
                        **{col: row[col] for col in work_df.columns},
                        **extracted_info
                    })
                else:
                    results.append({
                        'Zeile': processed,
                        **{col: row[col] for col in work_df.columns},
                        'Error': 'Keine gültige Homepage-URL vorhanden'
                    })
            except Exception as e:
                results.append({
                    'Zeile': processed,
                    **{col: row[col] for col in work_df.columns},
                    'Error': str(e)
                })

            progress_bar.progress(processed / max_rows)
            time.sleep(1)

        status_text.text("Fertig! ✅")
        st.session_state['scraped_results'] = results

        result_out_df = pd.DataFrame(results)
        st.success(f"✅ {len(results)} Zeilen bearbeitet")

        st.subheader("Ergebnisse")
        st.dataframe(result_out_df, use_container_width=True)

        csv = result_out_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Ergebnisse als CSV herunterladen",
            data=csv,
            file_name='scraped_ergebnisse.csv',
            mime='text/csv',
            key="download_results"
        )

# --- FOOTER ---
st.markdown("---")
st.caption("""
⚠️ **Rechtlicher Hinweis**: Stelle sicher, dass du die robots.txt der Zielseiten respektierst
und die Nutzungsbedingungen nicht verletzt. Vermeide zu häufige Anfragen.
""")
