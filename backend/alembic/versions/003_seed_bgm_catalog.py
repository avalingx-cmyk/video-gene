"""Seed royalty-free BGM catalog."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

revision = "003_seed_bgm_catalog"
down_revision = "002_assets_bgm_audit"
branch_labels = None
depends_on = None


ROYALTY_FREE_TRACKS = [
    # (title, artist, genre, duration_seconds, url, mood_tags, bpm)
    ("Ambient Dreamscape", "Free Music Archive", "ambient", 180.0, "https://freemusicarchive.org/music/ambient-dreamscape", "calm,peaceful,ethereal", 70),
    ("Chill Waves", "Pixabay Music", "lo-fi", 240.0, "https://pixabay.com/music/chill-waves", "chill,relaxed,smooth", 85),
    ("Cinematic Rise", "Uppbeat", "cinematic", 120.0, "https://uppbeat.io/browse/cinematic-rise", "epic,dramatic,building", 120),
    ("Corporate Tech", "Mixkit", "corporate", 90.0, "https://mixkit.co/free-stock-music/corporate-tech", "professional,modern,clean", 100),
    ("Energetic Vlog", "StreamBeats", "pop", 150.0, "https://www.streambeats.com/energetic-vlog", "upbeat,fun,energetic", 128),
    ("Gentle Piano", "Freesound", "piano", 200.0, "https://freesound.org/people/gentle-piano", "soft,melancholic,beautiful", 60),
    ("Hip Hop Beats", "YouTube Audio Library", "hip-hop", 175.0, "https://studio.youtube.com/audio-library/hip-hop-beats", "groovy,rhythmic,cool", 95),
    ("Inspirational Acoustic", "Epidemic Sound", "acoustic", 210.0, "https://www.epidemicsound.com/inspirational-acoustic", "motivational,warm,uplifting", 80),
    ("Jazz Lounge", "Free Music Archive", "jazz", 300.0, "https://freemusicarchive.org/music/jazz-lounge", "smooth,sophisticated,mellow", 110),
    ("Lo-fi Study", "Lofi Girl", "lo-fi", 360.0, "https://open.spotify.com/playlist/lofi-study", "study,focus,chill", 75),
    ("Nature Ambience", "Zapsplat", "ambient", 600.0, "https://www.zapsplat.com/nature-ambience", "nature,peaceful,background", 0),
    ("Neon Nights", "Pixabay Music", "electronic", 195.0, "https://pixabay.com/music/neon-nights", "synthwave,retro,stylish", 125),
    ("Piano Reflections", "Free Music Archive", "classical", 280.0, "https://freemusicarchive.org/music/piano-reflections", "reflective,calm,classical", 65),
    ("Upbeat Funk", "StreamBeats", "funk", 165.0, "https://www.streambeats.com/upbeat-funk", "fun,dance,colorful", 115),
    ("World Traveler", "Uppbeat", "world", 220.0, "https://uppbeat.io/browse/world-traveler", "exotic,adventurous,cultural", 90),
    ("Ambient Synth Pad", "Pixabay Music", "ambient", 300.0, "https://pixabay.com/music/ambient-synth-pad", "dreamy,floating,wide", 70),
    ("Soft Ukulele", "YouTube Audio Library", "acoustic", 140.0, "https://studio.youtube.com/audio-library/soft-ukulele", "happy,light,cheerful", 100),
    ("Electronic Pulse", "StreamBeats", "electronic", 185.0, "https://www.streambeats.com/electronic-pulse", "driving,tense,modern", 130),
    ("Orchestral Sweep", "Epidemic Sound", "cinematic", 160.0, "https://www.epidemicsound.com/orchestral-sweep", "grand,emotional,majestic", 85),
    ("Bossa Nova Sunset", "Free Music Archive", "jazz", 240.0, "https://freemusicarchive.org/music/bossa-nova-sunset", "relaxed,sunny,warm", 120),
]


def upgrade():
    op.bulk_insert(
        sa.table(
            "bgm_tracks",
            sa.Column("title", sa.String(255)),
            sa.Column("artist", sa.String(255)),
            sa.Column("genre", sa.String(100)),
            sa.Column("duration_seconds", sa.Float),
            sa.Column("url", sa.Text),
            sa.Column("mood_tags", sa.String(500)),
            sa.Column("bpm", sa.Integer),
            sa.Column("is_royalty_free", sa.Boolean),
            sa.Column("license_type", sa.String(100)),
            sa.Column("attribution_required", sa.Boolean),
            sa.Column("attribution_text", sa.Text),
            sa.Column("is_active", sa.Boolean),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "title": title,
                "artist": artist,
                "genre": genre,
                "duration_seconds": duration_seconds,
                "url": url,
                "mood_tags": mood_tags,
                "bpm": bpm,
                "is_royalty_free": True,
                "license_type": "royalty_free",
                "attribution_required": True if "Free Music Archive" in artist else False,
                "attribution_text": f"Music: {title} by {artist} — Royalty-free via {url.split('/')[2]}" if "Free Music Archive" in artist else None,
                "is_active": True,
                "created_at": datetime.utcnow(),
            }
            for title, artist, genre, duration_seconds, url, mood_tags, bpm in ROYALTY_FREE_TRACKS
        ],
    )


def downgrade():
    op.execute("DELETE FROM bgm_tracks")
