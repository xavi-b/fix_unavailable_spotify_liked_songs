import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
import json
import os

# ==== CONFIG ====
COUNTRY_CODE = "FR"  # Your region
OUTPUT_FILE = "unavailable_songs.csv"
CREDENTIALS_FILE = "spotify_credentials.json"

console = Console()

# ==== AUTH ====
# Create an app at https://developer.spotify.com/dashboard/
# Add "http://localhost:8080" as Redirect URI.
# Load credentials from JSON file
if not os.path.exists(CREDENTIALS_FILE):
    console.print(f"[bold red]Error: {CREDENTIALS_FILE} not found![/bold red]")
    console.print(f"Please create {CREDENTIALS_FILE} with your Spotify credentials:")
    console.print('{\n  "client_id": "your_client_id",\n  "client_secret": "your_client_secret",\n  "redirect_uri": "http://127.0.0.1:8080"\n}')
    exit(1)

with open(CREDENTIALS_FILE, 'r') as f:
    credentials = json.load(f)

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope="user-library-read user-library-modify",
    client_id=credentials['client_id'],
    client_secret=credentials['client_secret'],
    redirect_uri=credentials['redirect_uri']
))

# ==== FETCH ALL LIKED SONGS ====
def get_all_liked_tracks():
    results = sp.current_user_saved_tracks(limit=50)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return tracks

console.print("[bold cyan]Fetching all liked songs...[/bold cyan]")
all_tracks = get_all_liked_tracks()
console.print(f"🎧 [green]Fetched {len(all_tracks)} liked songs.[/green]\n")

# ==== CHECK AVAILABILITY ====
unavailable = []

for item in tqdm(all_tracks, desc="Checking availability", unit="song"):
    track = item['track']
    if not track:
        continue

    name = track.get('name', 'Unknown')
    artist = ', '.join(a['name'] for a in track.get('artists', []))
    track_id = track.get('id')
    is_playable = track.get('is_playable', True)
    available_markets = track.get('available_markets', [])

#    if not is_playable or COUNTRY_CODE not in available_markets:
    if not is_playable:
        unavailable.append({
            'Track Name': name,
            'Artist': artist,
            'Track ID': track_id,
            'Playable': is_playable,
            'Markets Count': len(available_markets)
        })

# ==== SAVE CSV ====
if unavailable:
    # Display in console
    table = Table(title="Unavailable Liked Songs")
    table.add_column("Track Name", style="bold red")
    table.add_column("Artist", style="cyan")
    table.add_column("Playable", justify="center")
    table.add_column("Markets", justify="center")

    for song in unavailable:  # show only first 30 in console
        table.add_row(song['Track Name'], song['Artist'], str(song['Playable']), str(song['Markets Count']))

    count = len(unavailable)
    console.print(f"\n🚫 [bold red]{count} unavailable songs detected![/bold red]")
    console.print(table)

    # Ask if user wants to remove unavailable songs
    console.print(f"\n❓ [bold yellow]Do you want to remove these {count} unavailable songs from your liked songs?[/bold yellow]")
    response = input("Type YES to remove them, or anything else to skip: ").strip()

    if response.upper() == "YES":
        console.print(f"\n🗑️  [bold cyan]Removing {count} unavailable songs from liked songs...[/bold cyan]")

        # Collect all track IDs
        track_ids = [song['Track ID'] for song in unavailable if song['Track ID']]

        # Remove tracks in batches (Spotify API limit is 50 per request)
        batch_size = 50
        removed_count = 0

        for i in tqdm(range(0, len(track_ids), batch_size), desc="Removing songs", unit="batch"):
            batch = track_ids[i:i + batch_size]
            try:
                sp.current_user_saved_tracks_delete(tracks=batch)
                removed_count += len(batch)
            except Exception as e:
                console.print(f"[bold red]Error removing batch: {e}[/bold red]")

        console.print(f"✅ [bold green]Successfully removed {removed_count} unavailable songs from your liked songs![/bold green]")
    else:
        console.print("[yellow]Skipping removal. Unavailable songs remain in your liked songs.[/yellow]")
else:
    console.print("✅ [bold green]All liked songs are available in your region![/bold green]")
