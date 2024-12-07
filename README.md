# SCOTUS Oral Argument Podcast

A podcast feed of oral argument audio from the Supreme Court of the United States. The feed is initially populated with the recording from the supremecourt.gov website. Metadata from oyez.org is added to the description of each episode. Once a transcript is available on [oyez.org](https://oyez.org/), it is used to add chapters to the episode (using [node-id3](https://www.npmjs.com/package/node-id3)), so it is possible to skip to the desired argument, or the desired exchange with a specific Justice. All the updating is done by a [Github Action](https://github.com/DominikPeters/scotus-podcast/blob/master/.github/workflows/build_podcast.yaml) that is
executed once per hour during weekday daytime.

The podcast feed is hosted at https://scotusstats.com/podcast/podcast.rss, and is available on [Apple Podcasts](https://podcasts.apple.com/us/podcast/supreme-court-oral-arguments/id1734053538), [Spotify](https://open.spotify.com/show/3fxexipVTGI255vbjckmgJ), and other podcast apps.
