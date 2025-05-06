import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def launch_driver():
    options = Options()

    # 🔧 Ne pas activer headless en debug (tu peux remettre --headless=new plus tard)
    # options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    # ❗ masque WebDriver pour éviter détection
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.maximize_window()
    return driver

def handle_cookie_popup(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
        ).click()
        print("🍪 Cookies acceptés.")
    except:
        print("✅ Pas de popup cookies détecté.")

def scrape_doctolib_results(driver, url, max_results=20):
    driver.get(url)
    print("🌐 Page chargée :", driver.current_url)

    handle_cookie_popup(driver)

    # ✅ Attente d’un praticien (titre "Dr" ou "Centre") pour s’assurer que les résultats ont bien chargé
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Dr') or contains(text(), 'Centre')]"))
        )
    except Exception as e:
        with open("debug_final_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        raise Exception("⚠️ Toujours aucun praticien visible après 20s. Contenu bloqué ?") from e

    time.sleep(2)

    cards = driver.find_elements(By.XPATH, "//h3[contains(text(), 'Dr') or contains(text(), 'Centre')]/ancestor::div[contains(@class, 'search-result')]")
    print(f"📦 {len(cards)} cartes détectées")

    results = []

    for card in cards[:max_results]:
        try:
            name = card.find_element(By.CSS_SELECTOR, "h3").text.strip()
        except:
            name = ""

        try:
            availability = card.find_element(By.CSS_SELECTOR, "div.availability-text").text.strip()
        except:
            availability = "Pas de disponibilité"

        try:
            times = card.find_elements(By.CSS_SELECTOR, "button[data-test='booking-time-button']")
            slots = [t.text.strip() for t in times if t.text.strip()]
            horaires_dispos = ", ".join(slots) if slots else availability
        except:
            horaires_dispos = availability

        consultation = "vidéo" if "vidéo" in card.text.lower() else "Cabinet"

        text_brut = card.text.lower()
        if "secteur 1" in text_brut:
            sector = "secteur 1"
        elif "secteur 2" in text_brut:
            sector = "secteur 2"
        elif "non conventionné" in text_brut:
            sector = "non conventionné"
        else:
            sector = "Inconnu"

        match = re.search(r"(\d+)\s?€", text_brut)
        price_text = match.group(1) + " €" if match else "Non renseigné"

        try:
            address_block = card.find_element(By.CSS_SELECTOR, ".dl-text.dl-text-body")
            lines = address_block.text.strip().split("\n")
            if len(lines) == 2:
                street = lines[0]
                postal_code = lines[1][:5]
                city = lines[1][6:]
            else:
                street, postal_code, city = "", "", ""
        except:
            street, postal_code, city = "", "", ""

        results.append({
            "Nom complet": name,
            "Prochaine disponibilité": availability,
            "Horaires visibles": horaires_dispos,
            "Consultation": consultation,
            "Secteur": sector,
            "Prix estimé (€)": price_text,
            "Rue": street,
            "Code postal": postal_code,
            "Ville": city
        })

    return results

def main():
    url = "https://www.doctolib.fr/search?location=paris&speciality=medecin-generaliste"
    driver = launch_driver()
    try:
        data = scrape_doctolib_results(driver, url, max_results=20)
    finally:
        driver.quit()

    if data:
        df = pd.DataFrame(data)
        df.to_csv("doctolib_paris_generalistes.csv", index=False, encoding="utf-8")
        print("✅ Export terminé → doctolib_paris_generalistes.csv")
    else:
        print("⚠️ Aucune donnée exportée.")

if __name__ == "__main__":
    main()
