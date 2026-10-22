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

`transcripts/` is gitignored because this repo is public and the transcripts are
the channel owner's content.

## Master outline

[`MASTER_OUTLINE.md`](MASTER_OUTLINE.md) organizes everything taught across the 13
[@PersonalBrandLaunch](https://www.youtube.com/@PersonalBrandLaunch) videos by
topic. Each concept covers what it is, how to apply it, and an example.

## Agent playbook

[`AGENT_PLAYBOOK.md`](AGENT_PLAYBOOK.md) is the step-by-step operating manual for an AI agent. It researches
outliers (ScrapeCreators), extracts their elements, builds fill-in-the-blank templates, and writes original scripts
for a client's niche (OpenRouter), with optional rendering (Hypit). In this repo, Claude Code picks it up as the
`short-form-content` skill (`.claude/skills/short-form-content/SKILL.md`). API keys go in environment variables
(`SCRAPECREATORS_API_KEY`, `OPENROUTER_API_KEY`, `SUPADATA_API_KEY`), never in files.
