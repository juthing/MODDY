import os
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image
from io import BytesIO
import json
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM


class DiscordBadgeDownloader:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Discord Badge Downloader")
        self.window.geometry("600x500")

        # URL du dépôt GitHub
        self.repo_api_url = "https://api.github.com/repos/mezotv/discord-badges/contents/assets"
        self.raw_base_url = "https://raw.githubusercontent.com/mezotv/discord-badges/main/assets/"

        # Liste des badges
        self.badges = []

        # Interface
        self.setup_ui()

        # Charger les badges
        self.load_badges()

    def setup_ui(self):
        # Titre
        title_label = tk.Label(self.window, text="Discord Badge Downloader",
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # Frame pour la liste
        list_frame = tk.Frame(self.window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Listbox pour afficher les badges
        self.badge_listbox = tk.Listbox(list_frame,
                                        yscrollcommand=scrollbar.set,
                                        font=("Arial", 10))
        self.badge_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.badge_listbox.yview)

        # Frame pour les boutons
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=10)

        # Bouton de téléchargement
        self.download_btn = tk.Button(button_frame,
                                      text="Télécharger en PNG",
                                      command=self.download_badge,
                                      bg="#5865F2",
                                      fg="white",
                                      font=("Arial", 12),
                                      padx=20,
                                      pady=5)
        self.download_btn.pack(side=tk.LEFT, padx=5)

        # Bouton rafraîchir
        refresh_btn = tk.Button(button_frame,
                                text="Rafraîchir",
                                command=self.load_badges,
                                font=("Arial", 12),
                                padx=20,
                                pady=5)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # Label de statut
        self.status_label = tk.Label(self.window, text="Chargement des badges...",
                                     fg="gray")
        self.status_label.pack(pady=5)

    def load_badges(self):
        """Charge la liste des badges depuis GitHub"""
        self.badge_listbox.delete(0, tk.END)
        self.badges = []
        self.status_label.config(text="Chargement des badges...")

        try:
            # Récupérer la liste des fichiers
            response = requests.get(self.repo_api_url)
            response.raise_for_status()

            files = response.json()

            # Filtrer les fichiers SVG
            svg_files = [f for f in files if f['name'].endswith('.svg')]

            # Ajouter à la liste
            for file in svg_files:
                badge_name = file['name'].replace('.svg', '')
                self.badges.append({
                    'name': badge_name,
                    'filename': file['name'],
                    'url': self.raw_base_url + file['name']
                })
                self.badge_listbox.insert(tk.END, badge_name)

            self.status_label.config(text=f"{len(self.badges)} badges trouvés")

        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les badges:\n{str(e)}")
            self.status_label.config(text="Erreur de chargement")

    def download_badge(self):
        """Télécharge le badge sélectionné en PNG"""
        selection = self.badge_listbox.curselection()

        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un badge")
            return

        badge_index = selection[0]
        badge = self.badges[badge_index]

        self.status_label.config(text=f"Téléchargement de {badge['name']}...")

        try:
            # Télécharger le SVG
            response = requests.get(badge['url'])
            response.raise_for_status()
            svg_data = response.content

            # Créer le dossier de téléchargement s'il n'existe pas
            download_folder = "discord_badges_png"
            if not os.path.exists(download_folder):
                os.makedirs(download_folder)

            # Sauvegarder temporairement le SVG
            temp_svg = f"temp_{badge['name']}.svg"
            with open(temp_svg, 'wb') as f:
                f.write(svg_data)

            # Convertir SVG en PNG avec svglib et reportlab
            try:
                drawing = svg2rlg(temp_svg)
                png_filename = os.path.join(download_folder, badge['name'] + '.png')
                renderPM.drawToFile(drawing, png_filename, fmt="PNG", dpi=300)

                # Redimensionner l'image si nécessaire
                img = Image.open(png_filename)
                img = img.resize((512, 512), Image.Resampling.LANCZOS)
                img.save(png_filename)

                self.status_label.config(text=f"Badge téléchargé: {png_filename}")
                messagebox.showinfo("Succès",
                                    f"Badge téléchargé avec succès!\n"
                                    f"Fichier: {png_filename}")

            finally:
                # Supprimer le fichier temporaire
                if os.path.exists(temp_svg):
                    os.remove(temp_svg)

        except Exception as e:
            messagebox.showerror("Erreur",
                                 f"Impossible de télécharger le badge:\n{str(e)}")
            self.status_label.config(text="Erreur de téléchargement")

    def run(self):
        """Lance l'application"""
        self.window.mainloop()


# Version alternative utilisant seulement PIL (sans conversion SVG native)
class DiscordBadgeDownloaderSimple:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Discord Badge Downloader")
        self.window.geometry("600x500")

        # URL du dépôt GitHub
        self.repo_api_url = "https://api.github.com/repos/mezotv/discord-badges/contents/assets"
        self.raw_base_url = "https://raw.githubusercontent.com/mezotv/discord-badges/main/assets/"

        # Liste des badges
        self.badges = []

        # Interface
        self.setup_ui()

        # Charger les badges
        self.load_badges()

    def setup_ui(self):
        # Titre
        title_label = tk.Label(self.window, text="Discord Badge Downloader",
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # Info
        info_label = tk.Label(self.window,
                              text="Note: Les badges seront téléchargés en SVG\n"
                                   "Utilisez un convertisseur SVG vers PNG si nécessaire",
                              fg="gray")
        info_label.pack()

        # Frame pour la liste
        list_frame = tk.Frame(self.window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Listbox pour afficher les badges
        self.badge_listbox = tk.Listbox(list_frame,
                                        yscrollcommand=scrollbar.set,
                                        font=("Arial", 10))
        self.badge_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.badge_listbox.yview)

        # Frame pour les boutons
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=10)

        # Bouton de téléchargement
        self.download_btn = tk.Button(button_frame,
                                      text="Télécharger SVG",
                                      command=self.download_badge,
                                      bg="#5865F2",
                                      fg="white",
                                      font=("Arial", 12),
                                      padx=20,
                                      pady=5)
        self.download_btn.pack(side=tk.LEFT, padx=5)

        # Bouton rafraîchir
        refresh_btn = tk.Button(button_frame,
                                text="Rafraîchir",
                                command=self.load_badges,
                                font=("Arial", 12),
                                padx=20,
                                pady=5)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # Label de statut
        self.status_label = tk.Label(self.window, text="Chargement des badges...",
                                     fg="gray")
        self.status_label.pack(pady=5)

    def load_badges(self):
        """Charge la liste des badges depuis GitHub"""
        self.badge_listbox.delete(0, tk.END)
        self.badges = []
        self.status_label.config(text="Chargement des badges...")

        try:
            # Récupérer la liste des fichiers
            response = requests.get(self.repo_api_url)
            response.raise_for_status()

            files = response.json()

            # Filtrer les fichiers SVG
            svg_files = [f for f in files if f['name'].endswith('.svg')]

            # Ajouter à la liste
            for file in svg_files:
                badge_name = file['name'].replace('.svg', '')
                self.badges.append({
                    'name': badge_name,
                    'filename': file['name'],
                    'url': self.raw_base_url + file['name']
                })
                self.badge_listbox.insert(tk.END, badge_name)

            self.status_label.config(text=f"{len(self.badges)} badges trouvés")

        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les badges:\n{str(e)}")
            self.status_label.config(text="Erreur de chargement")

    def download_badge(self):
        """Télécharge le badge sélectionné"""
        selection = self.badge_listbox.curselection()

        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un badge")
            return

        badge_index = selection[0]
        badge = self.badges[badge_index]

        self.status_label.config(text=f"Téléchargement de {badge['name']}...")

        try:
            # Télécharger le SVG
            response = requests.get(badge['url'])
            response.raise_for_status()
            svg_data = response.content

            # Créer le dossier de téléchargement s'il n'existe pas
            download_folder = "discord_badges_svg"
            if not os.path.exists(download_folder):
                os.makedirs(download_folder)

            # Sauvegarder le SVG
            svg_filename = os.path.join(download_folder, badge['filename'])
            with open(svg_filename, 'wb') as f:
                f.write(svg_data)

            self.status_label.config(text=f"Badge téléchargé: {svg_filename}")
            messagebox.showinfo("Succès",
                                f"Badge téléchargé avec succès!\n"
                                f"Fichier: {svg_filename}\n\n"
                                f"Pour convertir en PNG, utilisez un convertisseur en ligne\n"
                                f"ou un logiciel comme Inkscape.")

        except Exception as e:
            messagebox.showerror("Erreur",
                                 f"Impossible de télécharger le badge:\n{str(e)}")
            self.status_label.config(text="Erreur de téléchargement")

    def run(self):
        """Lance l'application"""
        self.window.mainloop()


if __name__ == "__main__":
    # Essayer d'abord avec la conversion SVG vers PNG
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM

        print("Lancement avec conversion SVG vers PNG...")
        app = DiscordBadgeDownloader()
        app.run()
    except ImportError:
        # Si les dépendances ne sont pas installées, utiliser la version simple
        print("Les dépendances pour la conversion SVG ne sont pas installées.")
        print("Utilisation de la version simple (téléchargement SVG uniquement).")
        print("\nPour la conversion SVG vers PNG, installez:")
        print("pip install svglib reportlab")
        print("\n" + "=" * 50 + "\n")

        app = DiscordBadgeDownloaderSimple()
        app.run()