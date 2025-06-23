import requests
import json


def get_guild_preview():
    guild_id = input("Entre l'ID du serveur Discord : ").strip()
    token = input("Token bot : ").strip()

    headers = {
        "Authorization": f"Bot {token}"
    }

    url = f"https://discord.com/api/v10/guilds/{guild_id}/preview"

    try:
        response = requests.get(url, headers=headers)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            except:
                print(f"Réponse: {response.text}")

    except Exception as e:
        print(f"Erreur: {e}")


if __name__ == "__main__":
    get_guild_preview()
