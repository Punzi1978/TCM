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
from urllib.parse import urljoin, urlparse
import io
from typing import List, Dict, Optional
import time

# Seite konfigurieren
st.set_page_config(
    page_title="PDF Tabellenscraper",
    page_icon="📊",
    layout="wide"
)

st.title("📄 PDF Tabellenscraper & Informations-Extraktor")
st.markdown("""
Diese Web-Anwendung:
1. Lädt eine PDF-Tabelle von einer URL herunter
2. Filtert und sortiert die Tabelle nach ausgewählten Spalten
3. Sucht für jede sichtbare Zeile Informationen auf verlinkten Homepages
4. Extrahiert Praxis-Namen, Mailadressen und weitere Details
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
                    tables = []
                    for i, page in enumerate(pdf.pages):
                        extracted_tables = page.extract_tables()
                        for j, table in enumerate(extracted_tables):
                            if table:
                                tables.append({
                                    'page': i + 1,
                                    'table_index': j + 1,
                                    'data': table
                                })

            if tables:
                st.success(f"{len(tables)} Tabelle(n) gefunden.")

                tab_selection = st.selectbox(
                    "Wähle die Tabelle zum Verarbeiten:",
                    [f"Tabelle {t['table_index']} auf Seite {t['page']}" for t in tables],
                    key="table_select"
                )

                selected_idx = int(tab_selection.split()[1]) - 1
                selected_table_data = tables[selected_idx]['data']

                # Konvertiere zu DataFrame
                df = pd.DataFrame(selected_table_data[1:], columns=selected_table_data[0])
                # Index neu setzen, damit er stabil bleibt (wichtig für Fortschrittsanzeige!)
                df = df.reset_index(drop=True)

                st.dataframe(df.head(), use_container_width=True)
                st.caption(f"Gesamte Zeilen: {len(df)}")

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

    use_filter = st.checkbox("Nur Zeilen anzeigen, die einen bestimmten Eintrag enthalten", value=True)

    filtered_df = df.copy()

    if use_filter:
        filter_col = st.selectbox(
            "Nach welcher Spalte filtern?",
            available_columns,
            key="filter_col"
        )
        search_text = st.text_input(
            "Welcher Eintrag soll enthalten sein? (z. B. Kanton, Stadt, Fachrichtung)",
            key="filter_text"
        )

        if search_text:
            mask = filtered_df[filter_col].astype(str).str.contains(
                search_text, case=False, na=False
            )
            filtered_df = filtered_df[mask]
            st.info(f"✅ {len(filtered_df)} von {len(df)} Zeilen entsprechen dem Filter.")
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

        # Sortierung anwenden
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

        # Gefilterte Tabelle auch herunterladbar machen
        csv_filtered = st.session_state['filtered_df'].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Gefilterte Tabelle als CSV herunterladen",
            data=csv_filtered,
            file_name='gefilterte_tabelle.csv',
            mime='text/csv',
            key="download_filtered"
        )

# --- SCHRITT 3: HOMEPAGE EXTRACTION ---
if st.session_state.get('sorted', False) and 'filtered_df' in st.session_state:
    st.header("Schritt 3: Informationen von Homepages extrahieren")

    work_df = st.session_state['filtered_df']

    col1, col2 = st.columns(2)

    with col1:
        homepage_col = st.selectbox(
            "Spalte mit Homepage-URL oder Name der Praxis:",
            st.session_state['df_columns'],
            key="homepage_col"
        )

    with col2:
        info_columns = st.multiselect(
            "Welche Informationen sollen extrahiert werden?",
            ["Name", "Mailadresse", "Telefon", "Adresse", "Über uns", "Dienstleistungen"],
            default=["Name", "Mailadresse"],
            key="info_cols"
        )

    st.info("""
    **Hinweis:**
    - Die Website muss öffentlich zugänglich sein
    - Manche Seiten benötigen JavaScript (dann funktioniert dies eventuell nicht vollständig)
    - Die App wartet 1 Sekunde zwischen Anfragen, um die Server zu schonen
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

        # WICHTIG: Mit eigenem Zähler arbeiten, nicht mit dem DataFrame-Index!
        processed = 0

        for _, row in work_df.head(max_rows).iterrows():
            processed += 1
            status_text.text(f"Verarbeite Zeile {processed}/{max_rows}")

            homepage_value = str(row[homepage_col]).strip()

            # Versuche URL zu bauen wenn nur Name angegeben
            if homepage_value and not homepage_value.lower().startswith(('http://', 'https://')):
                if '.' in homepage_value:  # sieht aus wie eine Domain
                    homepage_value = f"https://{homepage_value}"
                else:
                    # Suchbegriff aus Namen bauen
                    suche = homepage_value.replace(' ', '+')
                    homepage_value = f"Suche: {suche}"

            try:
                if homepage_value.startswith('http'):
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
                        'Error': f"Keine gültige URL gefunden ({homepage_value})"
                    })
            except Exception as e:
                results.append({
                    'Zeile': processed,
                    **{col: row[col] for col in work_df.columns},
                    'Error': str(e)
                })

            # Fortschritt mit Zähler (0.0 bis 1.0 garantiert)
            progress_bar.progress(processed / max_rows)
            time.sleep(1)  # Server schonen

        status_text.text("Fertig! ✅")
        st.session_state['scraped_results'] = results

        result_out_df = pd.DataFrame(results)
        st.success(f"✅ {len(results)} Websites bearbeitet")

        st.subheader("Ergebnisse")
        st.dataframe(result_out_df, use_container_width=True)

        # Download Button
        csv = result_out_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Ergebnisse als CSV herunterladen",
            data=csv,
            file_name='scraped_ergebnisse.csv',
            mime='text/csv',
            key="download_results"
        )

    # Falls bereits Ergebnisse vorhanden sind, weiterhin anzeigen
    elif st.session_state.get('scraped_results'):
        st.subheader("Letzte Ergebnisse")
        st.dataframe(pd.DataFrame(st.session_state['scraped_results']), use_container_width=True)

# --- HILFSFUNKTIONEN ---
def extract_site_information(url: str, info_types: List[str]) -> Dict[str, Optional[str]]:
    """
    Extrahiert verschiedene Informationen von einer Website
    """
    result = {}

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')

        # Titel/Name extrahieren
        if 'Name' in info_types:
            title_tag = soup.find('title')
            h1_tag = soup.find('h1')
            result['Name'] = title_tag.get_text().strip() if title_tag else (h1_tag.get_text().strip() if h1_tag else 'Nicht gefunden')

        # Mailadressen extrahieren
        if 'Mailadresse' in info_types:
            emails = extract_emails(response.text)
            result['Mailadresse'] = '; '.join(emails[:3]) if emails else 'Keine gefunden'

        # Telefonnummern extrahieren
        if 'Telefon' in info_types:
            phones = extract_phone_numbers(response.text)
            result['Telefon'] = '; '.join(phones[:3]) if phones else 'Keine gefunden'

        # Adresse extrahieren
        if 'Adresse' in info_types:
            addresses = extract_addresses(soup, response.text)
            result['Adresse'] = addresses[:2] if addresses else 'Keine gefunden'

        # Über uns Text
        if 'Über uns' in info_types:
            about_text = extract_about_section(soup)
            result['Über uns'] = about_text[:200] + '...' if about_text else 'Nicht gefunden'

        # Dienstleistungen
        if 'Dienstleistungen' in info_types:
            services = extract_services(soup)
            result['Dienstleistungen'] = '; '.join(services[:5]) if services else 'Keine gefunden'

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
    pattern = r'(?:\+\d{2}|0)\s*\(?[0-9]{2,5}\)?[\s.-]*[0-9\s.-]+'
    phones = re.findall(pattern, text)
    return list(set(phones))[:5]

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
    about_keywords = ['über uns', 'about us', 'unternehmen', 'firma', 'wir']

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

    lists = soup.find_all('ul', class_=re.compile(r'(service|angebot|dienstleistung)', re.I))

    for lst in lists[:2]:
        for li in lst.find_all('li')[:5]:
            services.append(li.get_text(strip=True))

    return services[:10]

# --- FOOTER ---
st.markdown("---")
st.caption("""
⚠️ **Rechtlicher Hinweis**: Stelle sicher, dass du die robots.txt der Zielseiten respektierst
und die Nutzungsbedingungen nicht verletzt. Vermeide zu häufige Anfragen.
""")
