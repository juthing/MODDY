import asyncio
from playwright.async_api import async_playwright
import tkinter as tk
from tkinter import scrolledtext

async def check_url(url, status_label, content_text):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until='domcontentloaded')

        # Obtenir le contenu de la page
        content = await page.content()

        content_text.delete(1.0, tk.END)  # Effacer le texte précédent
        content_text.insert(tk.END, content)  # Insérer le nouveau contenu
        status_label.config(text="Page chargée avec succès!")

        await browser.close()

def run_check_url():
    url = url_entry.get()
    asyncio.run(check_url(url, status_label, content_text))

# Création de la fenêtre principale
window = tk.Tk()
window.title("Vérificateur de Page avec Playwright")

# Champ de saisie pour l'URL
tk.Label(window, text="Entrez l'URL :").pack(pady=5)
url_entry = tk.Entry(window, width=50)
url_entry.pack(pady=5)

# Bouton pour vérifier l'URL
check_button = tk.Button(window, text="Vérifier", command=run_check_url)
check_button.pack(pady=10)

# Label pour afficher le code de statut
status_label = tk.Label(window, text="")
status_label.pack(pady=5)

# Zone de texte pour afficher le contenu de la réponse
content_text = scrolledtext.ScrolledText(window, wrap=tk.WORD, width=60, height=20)
content_text.pack(pady=10)

# Lancer la boucle principale de l'interface
window.mainloop()
