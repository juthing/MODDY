import requests
import json

# Ton token de bot
BOT_TOKEN = ''

# ID du salon
CHANNEL_ID = '1229085035358060699'

# Headers d'authentification
headers = {
    'Authorization': f'Bot {BOT_TOKEN}',
    'Content-Type': 'application/json'
}

# Payload sans les images
payload = {
    "flags": 32768,
    "components": [
        {
            "type": 17,
            "components": [
                {
                    "type": 10,
                    "content": "## Introducing New Components for Messages!\nWe're bringing new components to messages that you can use in your apps. They allow you to have full control over the layout of your messages.\n\nOur previous components system, while functional, had limitations:\n- Content, attachments, embeds, and components had to follow fixed positioning rules\n- Visual styling options were limited\n\nOur new component system addresses these challenges with fully composable components that can be arranged and laid out in any order, allowing for a more flexible and visually appealing design. Check out the [changelog](https://discord.com/developers/docs/change-log) for more details."
                },
                {
                    "type": 9,
                    "components": [
                        {
                            "type": 10,
                            "content": "A brief overview of components:"
                        }
                    ],
                    "accessory": {
                        "type": 2,
                        "style": 5,
                        "label": "Overview",
                        "url": "https://discord.com/developers/docs/components/overview"
                    }
                },
                {
                    "type": 9,
                    "components": [
                        {
                            "type": 10,
                            "content": "A list of all the components:"
                        }
                    ],
                    "accessory": {
                        "type": 2,
                        "style": 5,
                        "label": "Reference",
                        "url": "https://discord.com/developers/docs/components/reference#what-is-a-component-component-types"
                    }
                },
                {
                    "type": 9,
                    "components": [
                        {
                            "type": 10,
                            "content": "Get started with message components:"
                        }
                    ],
                    "accessory": {
                        "type": 2,
                        "style": 5,
                        "label": "Guide",
                        "url": "https://discord.com/developers/docs/components/using-message-components"
                    }
                },
                {
                    "type": 14
                },
                {
                    "type": 10,
                    "content": "-# This message was composed using components, check out the request:"
                }
            ]
        }
    ]
}

# Envoi du message via l'API Discord
response = requests.post(
    f'https://discord.com/api/v10/channels/{CHANNEL_ID}/messages',
    headers=headers,
    data=json.dumps(payload)
)

# Affichage du résultat
print(response.status_code)
print(response.text)
