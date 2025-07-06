import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
from datetime import datetime
import base64
from tkinter import filedialog


class WebhookManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Discord Webhook Manager")
        self.root.geometry("800x600")

        self.webhook_url = ""
        self.webhook_info = {}

        self.create_widgets()

    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # URL du webhook
        ttk.Label(main_frame, text="URL du Webhook:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_entry = ttk.Entry(main_frame, width=60)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Button(main_frame, text="Analyser", command=self.analyze_webhook).grid(row=0, column=3, pady=5, padx=5)

        # Informations du webhook
        info_frame = ttk.LabelFrame(main_frame, text="Informations du Webhook", padding="10")
        info_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)

        self.info_text = scrolledtext.ScrolledText(info_frame, width=70, height=8)
        self.info_text.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Actions
        actions_frame = ttk.LabelFrame(main_frame, text="Actions", padding="10")
        actions_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)

        # Boutons d'actions
        ttk.Button(actions_frame, text="Envoyer message", command=self.send_message).grid(row=0, column=0, pady=5,
                                                                                          padx=5)
        ttk.Button(actions_frame, text="Modifier webhook", command=self.modify_webhook).grid(row=0, column=1, pady=5,
                                                                                             padx=5)
        ttk.Button(actions_frame, text="Supprimer webhook", command=self.delete_webhook).grid(row=0, column=2, pady=5,
                                                                                              padx=5)
        ttk.Button(actions_frame, text="Rafraîchir", command=self.analyze_webhook).grid(row=0, column=3, pady=5, padx=5)

        # Configuration des poids pour le redimensionnement
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(0, weight=1)

    def is_valid_webhook_url(self, url):
        """Vérifie si l'URL est un webhook Discord valide"""
        # Patterns acceptés pour Discord
        valid_patterns = [
            "https://discord.com/api/webhooks/",
            "https://discordapp.com/api/webhooks/",
            "https://canary.discord.com/api/webhooks/",
            "https://ptb.discord.com/api/webhooks/"
        ]

        return any(url.startswith(pattern) for pattern in valid_patterns)

    def analyze_webhook(self):
        """Analyse le webhook et récupère ses informations"""
        url = self.url_entry.get().strip()

        if not url:
            messagebox.showerror("Erreur", "Veuillez entrer une URL de webhook")
            return

        if not self.is_valid_webhook_url(url):
            messagebox.showerror("Erreur", "URL de webhook invalide")
            return

        self.webhook_url = url

        try:
            response = requests.get(url)

            if response.status_code == 200:
                self.webhook_info = response.json()
                self.display_webhook_info()
                messagebox.showinfo("Succès", "Webhook analysé avec succès!")
            else:
                messagebox.showerror("Erreur",
                                     f"Impossible de récupérer les informations du webhook: {response.status_code}")

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Erreur", f"Erreur de connexion: {str(e)}")

    def display_webhook_info(self):
        """Affiche les informations du webhook"""
        self.info_text.delete(1.0, tk.END)

        info = f"""=== INFORMATIONS DU WEBHOOK ===

Nom: {self.webhook_info.get('name', 'Non défini')}
ID: {self.webhook_info.get('id', 'Non défini')}
Type: {self.webhook_info.get('type', 'Non défini')}
Canal ID: {self.webhook_info.get('channel_id', 'Non défini')}
Serveur ID: {self.webhook_info.get('guild_id', 'Non défini')}
Avatar: {'Oui' if self.webhook_info.get('avatar') else 'Non'}
Token: {self.webhook_info.get('token', 'Non défini')[:20]}...

=== DONNÉES BRUTES ===
{json.dumps(self.webhook_info, indent=2)}
"""

        self.info_text.insert(1.0, info)

    def send_message(self):
        """Ouvre une fenêtre pour envoyer un message"""
        if not self.webhook_url:
            messagebox.showerror("Erreur", "Veuillez d'abord analyser un webhook")
            return

        SendMessageWindow(self.root, self.webhook_url)

    def modify_webhook(self):
        """Ouvre une fenêtre pour modifier le webhook"""
        if not self.webhook_url:
            messagebox.showerror("Erreur", "Veuillez d'abord analyser un webhook")
            return

        ModifyWebhookWindow(self.root, self.webhook_url, self.webhook_info, self.analyze_webhook)

    def delete_webhook(self):
        """Supprime le webhook"""
        if not self.webhook_url:
            messagebox.showerror("Erreur", "Veuillez d'abord analyser un webhook")
            return

        result = messagebox.askyesno("Confirmation",
                                     "Êtes-vous sûr de vouloir supprimer ce webhook?\nCette action est irréversible!")

        if result:
            try:
                response = requests.delete(self.webhook_url)

                if response.status_code == 204:
                    messagebox.showinfo("Succès", "Webhook supprimé avec succès!")
                    self.webhook_url = ""
                    self.webhook_info = {}
                    self.info_text.delete(1.0, tk.END)
                    self.url_entry.delete(0, tk.END)
                else:
                    messagebox.showerror("Erreur", f"Impossible de supprimer le webhook: {response.status_code}")

            except requests.exceptions.RequestException as e:
                messagebox.showerror("Erreur", f"Erreur de connexion: {str(e)}")


class SendMessageWindow:
    def __init__(self, parent, webhook_url):
        self.webhook_url = webhook_url
        self.window = tk.Toplevel(parent)
        self.window.title("Envoyer un message")
        self.window.geometry("500x400")

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Nom d'utilisateur
        ttk.Label(main_frame, text="Nom d'utilisateur:").pack(anchor=tk.W, pady=5)
        self.username_entry = ttk.Entry(main_frame, width=50)
        self.username_entry.pack(fill=tk.X, pady=5)

        # Message
        ttk.Label(main_frame, text="Message:").pack(anchor=tk.W, pady=5)
        self.message_text = scrolledtext.ScrolledText(main_frame, width=50, height=10)
        self.message_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Boutons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Envoyer", command=self.send_message).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Annuler", command=self.window.destroy).pack(side=tk.LEFT, padx=5)

    def send_message(self):
        message = self.message_text.get(1.0, tk.END).strip()
        username = self.username_entry.get().strip()

        if not message:
            messagebox.showerror("Erreur", "Veuillez entrer un message")
            return

        data = {"content": message}
        if username:
            data["username"] = username

        try:
            response = requests.post(self.webhook_url, json=data)

            if response.status_code == 204:
                messagebox.showinfo("Succès", "Message envoyé avec succès!")
                self.window.destroy()
            else:
                messagebox.showerror("Erreur", f"Impossible d'envoyer le message: {response.status_code}")

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Erreur", f"Erreur de connexion: {str(e)}")


class ModifyWebhookWindow:
    def __init__(self, parent, webhook_url, webhook_info, refresh_callback):
        self.webhook_url = webhook_url
        self.webhook_info = webhook_info
        self.refresh_callback = refresh_callback
        self.window = tk.Toplevel(parent)
        self.window.title("Modifier le webhook")
        self.window.geometry("400x300")

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Nom
        ttk.Label(main_frame, text="Nom:").pack(anchor=tk.W, pady=5)
        self.name_entry = ttk.Entry(main_frame, width=40)
        self.name_entry.pack(fill=tk.X, pady=5)
        self.name_entry.insert(0, self.webhook_info.get('name', ''))

        # Avatar
        ttk.Label(main_frame, text="Avatar (optionnel):").pack(anchor=tk.W, pady=5)

        avatar_frame = ttk.Frame(main_frame)
        avatar_frame.pack(fill=tk.X, pady=5)

        self.avatar_path = tk.StringVar()
        ttk.Entry(avatar_frame, textvariable=self.avatar_path, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(avatar_frame, text="Parcourir", command=self.browse_avatar).pack(side=tk.RIGHT, padx=5)

        # Boutons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=20)

        ttk.Button(button_frame, text="Modifier", command=self.modify_webhook).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Annuler", command=self.window.destroy).pack(side=tk.LEFT, padx=5)

    def browse_avatar(self):
        filename = filedialog.askopenfilename(
            title="Sélectionner un avatar",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif")]
        )
        if filename:
            self.avatar_path.set(filename)

    def modify_webhook(self):
        name = self.name_entry.get().strip()

        if not name:
            messagebox.showerror("Erreur", "Veuillez entrer un nom")
            return

        data = {"name": name}

        # Traitement de l'avatar
        if self.avatar_path.get():
            try:
                with open(self.avatar_path.get(), 'rb') as f:
                    avatar_data = f.read()
                    avatar_b64 = base64.b64encode(avatar_data).decode('utf-8')

                    if self.avatar_path.get().lower().endswith('.jpg') or self.avatar_path.get().lower().endswith(
                            '.jpeg'):
                        mime_type = 'image/jpeg'
                    elif self.avatar_path.get().lower().endswith('.gif'):
                        mime_type = 'image/gif'
                    else:
                        mime_type = 'image/png'

                    data["avatar"] = f"data:{mime_type};base64,{avatar_b64}"
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de charger l'avatar: {str(e)}")
                return

        try:
            response = requests.patch(self.webhook_url, json=data)

            if response.status_code == 200:
                messagebox.showinfo("Succès", "Webhook modifié avec succès!")
                self.refresh_callback()
                self.window.destroy()
            else:
                messagebox.showerror("Erreur", f"Impossible de modifier le webhook: {response.status_code}")

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Erreur", f"Erreur de connexion: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = WebhookManager(root)
    root.mainloop()
