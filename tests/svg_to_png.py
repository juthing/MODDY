#!/usr/bin/env python3
"""
Convertisseur SVG vers PNG
Convertit plusieurs fichiers SVG en PNG 128x128 avec fond transparent
Version sans dépendances système
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading
import subprocess
import tempfile
import shutil

# Essayer d'importer les bibliothèques optionnelles
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM

    SVGLIB_AVAILABLE = True
except ImportError:
    SVGLIB_AVAILABLE = False


class SVGtoPNGConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("Convertisseur SVG vers PNG")
        self.root.geometry("500x450")
        self.root.resizable(False, False)

        # Variables
        self.files_to_convert = []
        self.is_converting = False
        self.conversion_method = None

        # Déterminer la méthode de conversion disponible
        self.check_conversion_methods()

        # Style
        style = ttk.Style()
        style.theme_use('clam')

        # Configuration des couleurs
        bg_color = "#f0f0f0"
        self.root.configure(bg=bg_color)

        # Frame principal
        main_frame = tk.Frame(root, bg=bg_color, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Titre
        title_label = tk.Label(
            main_frame,
            text="Convertisseur SVG → PNG",
            font=("Arial", 20, "bold"),
            bg=bg_color,
            fg="#333333"
        )
        title_label.pack(pady=(0, 20))

        # Description
        desc_label = tk.Label(
            main_frame,
            text="Convertit vos fichiers SVG en PNG 128×128 pixels\navec fond transparent",
            font=("Arial", 10),
            bg=bg_color,
            fg="#666666",
            justify=tk.CENTER
        )
        desc_label.pack(pady=(0, 20))

        # Méthode de conversion
        method_text = f"Méthode : {self.conversion_method if self.conversion_method else 'Aucune disponible'}"
        self.method_label = tk.Label(
            main_frame,
            text=method_text,
            font=("Arial", 8),
            bg=bg_color,
            fg="#999999"
        )
        self.method_label.pack(pady=(0, 10))

        # Bouton sélectionner
        self.select_button = tk.Button(
            main_frame,
            text="📁 Sélectionner des fichiers SVG",
            font=("Arial", 12),
            bg="#4CAF50",
            fg="white",
            activebackground="#45a049",
            activeforeground="white",
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.select_files,
            state=tk.NORMAL if self.conversion_method else tk.DISABLED
        )
        self.select_button.pack(pady=10)

        # Label fichiers sélectionnés
        self.files_label = tk.Label(
            main_frame,
            text="Aucun fichier sélectionné",
            font=("Arial", 10),
            bg=bg_color,
            fg="#999999"
        )
        self.files_label.pack(pady=10)

        # Progress bar
        self.progress = ttk.Progressbar(
            main_frame,
            mode='determinate',
            length=300
        )
        self.progress.pack(pady=20)
        self.progress.pack_forget()  # Cache au début

        # Label de progression
        self.progress_label = tk.Label(
            main_frame,
            text="",
            font=("Arial", 9),
            bg=bg_color,
            fg="#666666"
        )
        self.progress_label.pack()

        # Bouton convertir
        self.convert_button = tk.Button(
            main_frame,
            text="🔄 Convertir en PNG",
            font=("Arial", 12),
            bg="#2196F3",
            fg="white",
            activebackground="#0b7dda",
            activeforeground="white",
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.start_conversion,
            state=tk.DISABLED
        )
        self.convert_button.pack(pady=10)

        # Footer
        footer_label = tk.Label(
            main_frame,
            text="Les fichiers seront sauvegardés dans le dossier Téléchargements",
            font=("Arial", 8),
            bg=bg_color,
            fg="#999999"
        )
        footer_label.pack(side=tk.BOTTOM, pady=10)

        # Message d'erreur si aucune méthode disponible
        if not self.conversion_method:
            self.show_installation_help()

    def check_conversion_methods(self):
        """Vérifie les méthodes de conversion disponibles"""
        # Méthode 1: Inkscape (le plus fiable)
        if self.check_inkscape():
            self.conversion_method = "Inkscape"
            return

        # Méthode 2: svglib + reportlab
        if SVGLIB_AVAILABLE and PIL_AVAILABLE:
            self.conversion_method = "svglib"
            return

        # Méthode 3: ImageMagick
        if self.check_imagemagick():
            self.conversion_method = "ImageMagick"
            return

        self.conversion_method = None

    def check_inkscape(self):
        """Vérifie si Inkscape est installé"""
        try:
            result = subprocess.run(['inkscape', '--version'],
                                    capture_output=True,
                                    text=True,
                                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            return result.returncode == 0
        except:
            return False

    def check_imagemagick(self):
        """Vérifie si ImageMagick est installé"""
        try:
            # Sur Windows, la commande est souvent 'magick' au lieu de 'convert'
            cmd = 'magick' if sys.platform == "win32" else 'convert'
            result = subprocess.run([cmd, '--version'],
                                    capture_output=True,
                                    text=True,
                                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            return result.returncode == 0
        except:
            return False

    def show_installation_help(self):
        """Affiche l'aide pour installer les dépendances"""
        help_text = """Aucune méthode de conversion n'est disponible.

Pour utiliser ce convertisseur, installez l'une des options suivantes :

Option 1 (Recommandée) - Inkscape :
• Téléchargez Inkscape depuis inkscape.org
• Installez-le avec les paramètres par défaut

Option 2 - Bibliothèques Python :
• pip install svglib reportlab pillow

Option 3 - ImageMagick :
• Téléchargez depuis imagemagick.org
• Installez avec l'option "Install legacy utilities"

Après l'installation, redémarrez ce programme."""

        messagebox.showinfo("Installation requise", help_text)

    def select_files(self):
        """Ouvre le dialogue de sélection de fichiers"""
        files = filedialog.askopenfilenames(
            title="Sélectionner des fichiers SVG",
            filetypes=[("Fichiers SVG", "*.svg"), ("Tous les fichiers", "*.*")],
            initialdir=os.path.expanduser("~")
        )

        if files:
            self.files_to_convert = [f for f in files if f.lower().endswith('.svg')]

            if not self.files_to_convert:
                messagebox.showwarning(
                    "Attention",
                    "Aucun fichier SVG valide n'a été sélectionné."
                )
                return

            # Mise à jour de l'interface
            count = len(self.files_to_convert)
            self.files_label.config(
                text=f"{count} fichier{'s' if count > 1 else ''} SVG sélectionné{'s' if count > 1 else ''}",
                fg="#333333"
            )
            self.convert_button.config(state=tk.NORMAL)

    def get_downloads_folder(self):
        """Obtient le dossier Téléchargements de l'utilisateur"""
        # Windows
        if sys.platform == "win32":
            import winreg
            sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
            downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                location = winreg.QueryValueEx(key, downloads_guid)[0]
            return location
        # macOS et Linux
        else:
            return os.path.join(os.path.expanduser('~'), 'Downloads')

    def convert_svg_to_png(self, svg_path, png_path):
        """Convertit un fichier SVG en PNG selon la méthode disponible"""
        if self.conversion_method == "Inkscape":
            return self.convert_with_inkscape(svg_path, png_path)
        elif self.conversion_method == "svglib":
            return self.convert_with_svglib(svg_path, png_path)
        elif self.conversion_method == "ImageMagick":
            return self.convert_with_imagemagick(svg_path, png_path)
        return False

    def convert_with_inkscape(self, svg_path, png_path):
        """Convertit avec Inkscape"""
        try:
            cmd = [
                'inkscape',
                svg_path,
                '--export-type=png',
                f'--export-filename={png_path}',
                '--export-width=128',
                '--export-height=128',
                '--export-background-opacity=0'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            return result.returncode == 0 and os.path.exists(png_path)
        except Exception as e:
            print(f"Erreur Inkscape : {e}")
            return False

    def convert_with_svglib(self, svg_path, png_path):
        """Convertit avec svglib et PIL"""
        try:
            # Convertir SVG en drawing
            drawing = svg2rlg(svg_path)
            if not drawing:
                return False

            # Créer un fichier temporaire
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                temp_path = tmp.name

            # Rendre en PNG
            renderPM.drawToFile(drawing, temp_path, fmt="PNG")

            # Redimensionner avec PIL
            img = Image.open(temp_path)

            # Convertir en RGBA si nécessaire
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            # Redimensionner à 128x128
            img_resized = img.resize((128, 128), Image.Resampling.LANCZOS)

            # Sauvegarder
            img_resized.save(png_path, 'PNG')

            # Nettoyer
            os.unlink(temp_path)

            return True
        except Exception as e:
            print(f"Erreur svglib : {e}")
            return False

    def convert_with_imagemagick(self, svg_path, png_path):
        """Convertit avec ImageMagick"""
        try:
            cmd_name = 'magick' if sys.platform == "win32" else 'convert'
            cmd = [
                cmd_name,
                '-background', 'none',
                '-density', '300',
                '-resize', '128x128',
                svg_path,
                png_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            return result.returncode == 0 and os.path.exists(png_path)
        except Exception as e:
            print(f"Erreur ImageMagick : {e}")
            return False

    def start_conversion(self):
        """Lance la conversion dans un thread séparé"""
        if self.is_converting:
            return

        # Désactiver les boutons
        self.select_button.config(state=tk.DISABLED)
        self.convert_button.config(state=tk.DISABLED)
        self.is_converting = True

        # Afficher la barre de progression
        self.progress.pack(pady=20)
        self.progress['maximum'] = len(self.files_to_convert)
        self.progress['value'] = 0

        # Lancer la conversion dans un thread
        thread = threading.Thread(target=self.convert_files)
        thread.start()

    def convert_files(self):
        """Convertit tous les fichiers sélectionnés"""
        downloads_folder = self.get_downloads_folder()
        success_count = 0
        error_files = []

        for i, svg_file in enumerate(self.files_to_convert):
            # Mise à jour de la progression
            self.root.after(0, self.update_progress, i + 1, len(self.files_to_convert))

            # Nom du fichier de sortie
            svg_name = Path(svg_file).stem
            png_name = f"{svg_name}.png"
            png_path = os.path.join(downloads_folder, png_name)

            # Gérer les doublons
            counter = 1
            while os.path.exists(png_path):
                png_name = f"{svg_name}_{counter}.png"
                png_path = os.path.join(downloads_folder, png_name)
                counter += 1

            # Convertir
            if self.convert_svg_to_png(svg_file, png_path):
                success_count += 1
            else:
                error_files.append(os.path.basename(svg_file))

        # Fin de la conversion
        self.root.after(0, self.conversion_complete, success_count, error_files)

    def update_progress(self, current, total):
        """Met à jour la barre de progression"""
        self.progress['value'] = current
        self.progress_label.config(
            text=f"Conversion en cours... {current}/{total}"
        )

    def conversion_complete(self, success_count, error_files):
        """Appelé quand la conversion est terminée"""
        self.is_converting = False

        # Réactiver les boutons
        self.select_button.config(state=tk.NORMAL)
        self.convert_button.config(state=tk.NORMAL)

        # Cacher la barre de progression
        self.progress.pack_forget()
        self.progress_label.config(text="")

        # Message de fin
        total = len(self.files_to_convert)
        if success_count == total:
            messagebox.showinfo(
                "Conversion terminée",
                f"✅ {success_count} fichier{'s' if success_count > 1 else ''} "
                f"converti{'s' if success_count > 1 else ''} avec succès !\n\n"
                f"Les fichiers sont dans le dossier Téléchargements."
            )
        else:
            error_msg = f"⚠️ {success_count}/{total} fichiers convertis.\n\n"
            if error_files:
                error_msg += "Erreurs sur :\n" + "\n".join(f"• {f}" for f in error_files[:5])
                if len(error_files) > 5:
                    error_msg += f"\n... et {len(error_files) - 5} autres"
            messagebox.showwarning("Conversion partielle", error_msg)

        # Réinitialiser
        self.files_to_convert = []
        self.files_label.config(
            text="Aucun fichier sélectionné",
            fg="#999999"
        )
        self.convert_button.config(state=tk.DISABLED)


def main():
    # Créer l'application
    root = tk.Tk()
    app = SVGtoPNGConverter(root)
    root.mainloop()


if __name__ == "__main__":
    main()