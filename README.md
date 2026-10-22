# GoCrazy

## Channel transcripts

`supadata_transcripts.py` lists every upload on a YouTube channel with the
[Supadata API](https://docs.supadata.ai) and saves each video's transcript.

```bash
pip install -r requirements.txt
cp .env.example .env            # then put your Supadata key in .env
python supadata_transcripts.py https://www.youtube.com/@SomeChannel
```

Output goes to `transcripts/`:

- `<title> [<id>].txt`: readable transcript, one timestamped caption per line
- `<id>.json`: video metadata plus the raw transcript chunks
- `index.json`: one row per video with its title, date, file and any error

Credits: 1 for the channel listing, plus about 2 per video (metadata and
transcript). Use `--no-metadata` to halve that. The default `--mode native` only
uses captions that YouTube already has. `--mode auto` falls back to AI
transcription for videos without captions, which costs more. Re-running skips
videos that are already downloaded.
