### 📄 Instructions pour les IAs – Projet Moddy

Tu aides à développer **Moddy**, un bot Discord écrit en **Python**, hébergé sur un **VPS Ubuntu 24.04 LTS** (chez Hostinger). Il s'agit d'une **application publique**, orientée **assistance pour modérateurs et administrateurs**, mais **sans commandes de sanction** classiques.

#### 📦 Stack et structure

* **Langage** : Python 3.11+
* **Lib** : `discord.py` avec support des **components v2** de Discord
* **Base de données** : Neon (PostgreSQL)
* **Variables d’environnement** via `.env`
* **Arborescence actuelle** :

  ```
  MODDY/
  ├── main.py          # Le cerveau du bot
  ├── init.py          # Initialisation du bot
  ├── config.py        # Configuration (token, etc.)
  ├── cogs/            # Dossier des modules utilisateurs
  │   └── __init__.py
  ├── staff/           # Dossier des commandes staff/dev
  │   └── __init__.py
  ├── requirements.txt # Dépendances Python
  └── .env             # Variables d'environnement (token Discord)
  ```

#### 🛠️ Commandes développeur

Ces commandes sont accessibles **partout (même en DM)**, en mentionnant le bot avec la commande, par ex. : `<@BOTID> reboot`. Elles sont situées dans le dossier `staff/`. Exemples :

* `reboot`
* `user`
* `server`
* `ping`
* `version`
* `sync`
* `deploy` (déploiement d’un commit sur le VPS)

#### 🎯 Commandes slash disponibles

Commandes principales organisées en plusieurs catégories (à coder avec des cogs bien structurés) :

* **Lookup / Informations** :

  * `/user lookup`
  * `/guild lookup`
  * `/event lookup` `[Server Invite] [Event ID]`
  * `/invite lookup`
  * `/webhook lookup`
  * `/avatar` (serveur ou utilisateur)
  * `/banner`

* **Outils et utilitaires** :

  * `/translate [content] | [from] [to]`
  * `/emoji`
  * `/OCR`
  * `/dictionary`
  * `/timestamp syntax`
  * `/roll [min] [max]`

* **Rappels** :

  * `/reminder add`
  * `/reminder remove`
  * `/reminder list`

* **Tags personnalisés** :

  * `/tag send`
  * `/tag manage`

* **Moddy (infos bot)** :

  * `/moddy invite`
  * `/moddy info`
  * `/moddy code`
  * `/preferences`
  * `/help`

#### 📋 Règles et style

* Moddy doit être **modulaire, propre et scalable**.
* Réponses et messages en **français uniquement**.
* Utilise **les components V2** pour les embeds (pas d’anciens systèmes).
* Priorité à la clarté, la fiabilité et la maintenabilité du code.
* Aucun système de modération classique (pas de ban/kick/warn).
* Prévois la prise en charge d’**interactions contextuelles** (menus, boutons, réponses dynamiques).
* Les commandes peuvent être regroupées dans des cogs selon leur thème (lookup, outils, rappels, etc.).

