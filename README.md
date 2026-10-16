# campus-watch

Watches the Atlético de Madrid Christmas campus pages every ~5 minutes (GitHub Actions)
and sends a phone push via ntfy when the Christmas campus information changes.

- Phone: ntfy app, subscribed to the topic set in `.github/workflows/watch.yml`
- Run manually: Actions tab → campus-watch → Run workflow
- Stop: Actions tab → campus-watch → ⋯ → Disable workflow
