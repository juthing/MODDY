import requests
import json


def test_webhook_basic(webhook_url):
    """Test basique du webhook"""
    print("🔍 Test 1: Message simple...")

    simple_message = {
        "content": "✅ Test webhook Moddy - Message simple"
    }

    response = requests.post(webhook_url, json=simple_message)
    print(f"Status: {response.status_code}")

    if response.status_code == 204:
        print("✅ Webhook fonctionne !")
        return True
    else:
        print(f"❌ Erreur: {response.status_code}")
        print(response.text)
        return False


def test_webhook_embed(webhook_url):
    """Test avec embed classique"""
    print("\n🔍 Test 2: Message avec embed...")

    embed_message = {
        "content": "Message avec embed :",
        "embeds": [
            {
                "title": "🤖 Bot Moddy",
                "description": "Interface de modération moderne",
                "color": 0x5865F2,
                "fields": [
                    {
                        "name": "Status",
                        "value": "✅ Opérationnel",
                        "inline": True
                    },
                    {
                        "name": "Version",
                        "value": "2.0",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Moddy Bot • Créé par Jules"
                }
            }
        ]
    }

    response = requests.post(webhook_url, json=embed_message)
    print(f"Status: {response.status_code}")

    if response.status_code == 204:
        print("✅ Embed envoyé avec succès !")
        return True
    else:
        print(f"❌ Erreur: {response.status_code}")
        print(response.text)
        return False


def test_new_components(webhook_url):
    """Test avec nouveaux components"""
    print("\n🔍 Test 3: Nouveaux components...")

    new_components = {
        "content": "Test nouveaux components :",  # Fallback obligatoire
        "flags": 32768,
        "components": [
            {
                "type": 17,
                "components": [
                    {
                        "type": 10,
                        "content": "## 🚀 Nouveaux Components Discord\n\nCe message utilise la nouvelle API components !"
                    },
                    {
                        "type": 14  # Separator
                    },
                    {
                        "type": 10,
                        "content": "*Layout flexible sans bande de couleur*"
                    }
                ]
            }
        ]
    }

    response = requests.post(webhook_url, json=new_components)
    print(f"Status: {response.status_code}")

    if response.status_code == 204:
        print("✅ Nouveaux components envoyés !")
        return True
    else:
        print(f"❌ Erreur: {response.status_code}")
        print(response.text)
        return False


def main():
    """Fonction principale"""
    print("🤖 === TEST WEBHOOK MODDY === 🤖\n")

    # Ton URL webhook
    webhook_url = "https://discord.com/api/webhooks/1391424210961694781/dcVCtC52_9soHMB7K5q2tt63Sml_j1cfUIU8XFnOt9WPMBAgGuInXtpcLiSaJ7XAFLzH"

    # Tests progressifs
    if test_webhook_basic(webhook_url):
        if test_webhook_embed(webhook_url):
            test_new_components(webhook_url)
        else:
            print("⚠️ Embed ne fonctionne pas, pas la peine de tester les nouveaux components")
    else:
        print("❌ Webhook non fonctionnel, vérifie ton URL !")


if __name__ == "__main__":
    main()
