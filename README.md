# Doctolib Scraper

## Description
Cette application est une interface Flask combinée avec Selenium pour scraper des données depuis Doctolib. Elle permet de rechercher des professionnels de santé, d'appliquer des filtres, et de télécharger les résultats sous forme de fichier CSV.

## Prérequis
- Python 3.8 ou supérieur
- Google Chrome installé
- ChromeDriver correspondant à la version de Chrome installée

## Installation

1. Clonez ce dépôt ou téléchargez les fichiers.
2. Créez un environnement virtuel Python :
   ```bash
   python -m venv venv
   ```
3. Activez l'environnement virtuel :
   - Sur Windows :
     ```bash
     .\venv\Scripts\activate
     ```
   - Sur macOS/Linux :
     ```bash
     source venv/bin/activate
     ```
4. Installez les dépendances nécessaires :
   ```bash
   pip install -r requirements.txt
   ```

## Utilisation

1. Lancez l'application Flask :
   ```bash
   python app.py
   ```
2. Ouvrez votre navigateur et accédez à [http://localhost:5000](http://localhost:5000).
3. Remplissez le formulaire pour effectuer une recherche sur Doctolib.
4. Téléchargez les résultats sous forme de fichier CSV.

## Notes
- Assurez-vous que ChromeDriver est dans votre PATH ou dans le même répertoire que le script.
- En cas d'erreur, des captures d'écran (`general_error.png` et `timeout_error.png`) seront générées pour aider au débogage.

## Dépendances
- Flask
- Selenium

## Auteurs
- Lucas

## Licence
Ce projet est sous licence MIT.