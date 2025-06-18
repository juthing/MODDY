import requests
import json


def get_application_info():
    print("=== Discord Application Lookup ===\n")

    # Demander les infos nécessaires
    app_id = input("Entre l'ID de l'application Discord : ").strip()

    # Optionnel : token bot (on teste d'abord sans)
    use_token = input("Veux-tu utiliser un token bot ? (y/n) : ").strip().lower()

    headers = {
        "User-Agent": "DiscordBot (https://github.com/discordlookup, 1.0)",
        "Content-Type": "application/json"
    }

    if use_token == 'y':
        bot_token = input("Entre ton token bot : ").strip()
        headers["Authorization"] = f"Bot {bot_token}"

    # Construire l'URL
    url = f"https://discord.com/api/v10/applications/{app_id}/rpc"

    print(f"\n🔍 Recherche des infos pour l'application : {app_id}")
    print(f"📡 URL : {url}\n")

    try:
        # Faire la requête
        response = requests.get(url, headers=headers)

        print(f"📊 Status Code : {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Succès ! Voici les données :\n")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print("❌ Erreur dans la réponse :")
            print(f"Status : {response.status_code}")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except:
                print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de requête : {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Erreur JSON : {e}")
        print(f"Réponse brute : {response.text}")


if __name__ == "__main__":
    get_application_info()

    # Demander si on veut refaire une recherche
    while True:
        again = input("\nVeux-tu faire une autre recherche ? (y/n) : ").strip().lower()
        if again == 'y':
            print("\n" + "=" * 50 + "\n")
            get_application_info()
        else:
            print("👋 À bientôt Jules !")
            break
