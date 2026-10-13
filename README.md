# SCOTUS Oral Argument Podcast

A podcast feed of oral argument audio from the Supreme Court of the United States. Court recordings are added as soon as they are available. Aligned transcripts from the video pipeline supply chapters and VTT transcripts as soon as alignment finishes, independently of video rendering or photo approval. Oyez supplies case descriptions when available and remains the alignment fallback for recordings that have no cloud alignment.

The [GitHub workflow](https://github.com/DominikPeters/scotus-podcast/blob/master/.github/workflows/build_podcast.yaml) runs hourly during weekday daytime and receives `scotus_alignment_ready` repository dispatches from the video controller. The same chapter naming and grouping rules apply to both alignment providers. Episode GUIDs and audio URLs remain stable when chapters are added or revised. Audio is tagged without re-encoding, and changed media is uploaded before the RSS feeds are replaced.

The bridge reads the public, immutable alignment exports indexed at https://scotusstats.com/podcast/alignment/index.json. Exports contain recording metadata, speaker names and timed transcript text; cloud credentials and private review notes are excluded. An export revision is imported once. Later Oyez metadata updates do not replace cloud chapters or audio. A second hearing for an existing docket is held for an owner decision instead of overwriting that episode.

Use `python3 get_alignment.py --dry-run` to inspect exports without downloading audio or changing feeds. The manual workflow also has a `dry_run` input. Repository variable `SCOTUS_BRIDGE_DRY_RUN=true` keeps all workflow triggers in dry-run mode during deployment checks. Tests run with `python3 -m unittest discover -p 'test_*.py'`.

The podcast feed is hosted at https://scotusstats.com/podcast/podcast.rss, and is available on [Apple Podcasts](https://podcasts.apple.com/us/podcast/supreme-court-oral-arguments/id1734053538), [Spotify](https://open.spotify.com/show/3fxexipVTGI255vbjckmgJ), and other podcast apps.
