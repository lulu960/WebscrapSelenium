#!/usr/bin/env python3
"""
app.py: Interface Flask + Selenium pour scraper Doctolib
Usage:
    1. Démarrer l’app : python3 app.py
    2. Ouvrir http://localhost:5000
    3. Remplir le formulaire et cliquer sur "Rechercher"
    4. Télécharger le CSV généré
"""
import logging
import datetime
import csv
import io

from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- Configuration des logs ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

app = Flask(__name__)
app.secret_key = 'change_this_to_a_secure_random_key'


def init_driver(headless=False):
    logging.info("Initialisation du driver Chrome (headless=%s)", headless)
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    return driver


def accept_cookies(driver):
    logging.info("Vérification bannière cookies")
    wait = WebDriverWait(driver, 5)
    try:
        btn = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            "button#didomi-notice-agree-button, button[aria-label='Tout accepter'], button[aria-label='Autoriser']"
        )))
        btn.click()
        logging.info("Cookies acceptés")
    except TimeoutException:
        logging.info("Pas de bannière cookies détectée")


def format_date(date_str):
    return datetime.datetime.strptime(date_str, '%d/%m/%Y').date()


def apply_filters(driver, form):
    logging.info("Application des filtres → assurance=%s, consultation=%s",
                 form.get('assurance'), form.get('consultation'))
    if form.get('assurance'):
        try:
            driver.find_element(By.XPATH,
                f"//label[contains(., '{form['assurance']}')]"
            ).click()
            logging.info("Filtre assurance cliqué")
        except Exception:
            logging.warning("Filtre assurance introuvable")
    if form.get('consultation'):
        key = 'Visio' if form['consultation'] == 'video' else 'Sur place'
        try:
            driver.find_element(By.XPATH,
                f"//label[contains(., '{key}')]"
            ).click()
            logging.info("Filtre consultation cliqué: %s", key)
        except Exception:
            logging.warning("Filtre consultation '%s' introuvable", key)


def extract_data(card):
    logging.info("Extraction données carte")
    # Nom
    try:
        name = card.find_element(By.TAG_NAME, "h2").text
    except NoSuchElementException:
        name = ''
        logging.warning("Nom introuvable")

    # Prochaine dispo
    dispo = ''
    try:
        slots = card.find_elements(By.CSS_SELECTOR, "[data-test='available-slot']")
        if slots:
            dispo = slots[0].text
    except Exception:
        logging.debug("Aucune dispo trouvée")

    # Type
    consult = 'Visio' if 'Visio' in card.text else 'Sur place'

    # Secteur
    sector = ''
    try:
        sector = card.find_element(
            By.XPATH, ".//p[contains(., 'Conventionné')]"
        ).text
    except NoSuchElementException:
        logging.debug("Secteur introuvable")

    # Prix
    price = None
    try:
        text = card.find_element(By.CSS_SELECTOR, "span[data-testid='price-info']").text
        price = int(''.join(filter(str.isdigit, text)))
    except Exception:
        logging.debug("Prix via data-testid introuvable, fallback regex")
        import re
        m = re.search(r'(\d+)\s*€', card.text)
        if m:
            price = int(m.group(1))

    # Adresse (nouveau sélecteur)
    street = postal = city = ''
    try:
        svg_loc = card.find_element(By.CSS_SELECTOR, "svg[data-icon-name='regular/location-dot']")
        # le <svg> est dans un <div>, son sibling suivant contient les <p> de l'adresse
        addr_div = svg_loc.find_element(By.XPATH, "../following-sibling::div")
        p_tags = addr_div.find_elements(By.TAG_NAME, "p")
        if len(p_tags) >= 1:
            street = p_tags[0].text
        if len(p_tags) >= 2:
            postal_city = p_tags[1].text
            parts = postal_city.split(" ", 1)
            postal = parts[0]
            city = parts[1] if len(parts) > 1 else ''
    except Exception:
        logging.warning("Adresse introuvable avec le nouveau sélecteur")

    row = [name, dispo, consult, sector, price, street, postal, city]
    logging.info("Ligne extraite: %s", row)
    return row


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        logging.info("Formulaire reçu: %s", request.form.to_dict())
        # Validation dates
        try:
            format_date(request.form.get('start_date') or '01/01/1970')
            format_date(request.form.get('end_date')   or '31/12/2099')
        except Exception:
            flash('Format de date invalide. Utilisez JJ/MM/AAAA.')
            logging.error("Format de date invalide")
            return redirect(url_for('index'))

        driver = init_driver(headless=False)
        wait = WebDriverWait(driver, 20)
        try:
            driver.get('https://www.doctolib.fr/')
            accept_cookies(driver)

            # Requête (obligatoire)
            q = request.form['query']
            logging.info("Recherche: '%s'", q)
            inp = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input.searchbar-query-input")
            ))
            inp.clear(); inp.send_keys(q)
            wait.until(lambda d: inp.get_attribute("aria-expanded") == "true")
            inp.send_keys(Keys.ENTER)
            logging.info("Requête validée")

            # Adresse (facultative)
            addr = request.form.get('address','').strip()
            if addr:
                logging.info("Saisie adresse: '%s'", addr)
                loc = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input.searchbar-place-input")
                ))
                loc.clear(); loc.send_keys(addr)
                wait.until(lambda d: loc.get_attribute("aria-expanded") == "true")
                loc.send_keys(Keys.ENTER)
                logging.info("Adresse validée")

            # Lancer la recherche
            btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.searchbar-submit-button")
            ))
            btn.click()
            logging.info("Bouton Rechercher cliqué")

            # Attente des cartes
            try:
                wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "article.dl-p-doctor-result-card")
                ))
                logging.info("Cartes résultats chargées")
            except TimeoutException:
                logging.error("Timeout attente des résultats")
                flash("Aucun résultat ou page trop lente.")
                return redirect(url_for('index'))

            apply_filters(driver, request.form)

            cards = driver.find_elements(By.CSS_SELECTOR, "article.dl-p-doctor-result-card")
            logging.info("Nombre de cartes: %d", len(cards))
            maxr = int(request.form.get('max_results') or 10)
            rows = [extract_data(card) for card in cards[:maxr]]

        except Exception:
            logging.exception("Erreur durant le scraping")
            flash("Une erreur est survenue lors du scraping.")
            return redirect(url_for('index'))
        finally:
            driver.quit()
            logging.info("Driver fermé")

        # Génération du CSV
        si = io.StringIO()
        w = csv.writer(si)
        w.writerow(['Nom','Prochaine dispo','Type','Secteur','Prix (€)','Rue','CP','Ville'])
        w.writerows(rows)
        si.seek(0)
        logging.info("Envoi du CSV")
        return send_file(
            io.BytesIO(si.read().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='doctolib_results.csv'
        )

    logging.info("Affichage formulaire")
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
