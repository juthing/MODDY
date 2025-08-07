import sys
from pathlib import Path

# Ensure project root is on sys.path for direct imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.embeds import ModdyEmbed

def test_timestamp_is_timezone_aware():
    embed = ModdyEmbed.create(description="desc", timestamp=True)
    assert embed.timestamp is not None
    assert embed.timestamp.tzinfo is not None
