# FeedSync - Hanwha News & Social Exporter

Collect the latest Hanwha Group newsroom press releases and social media updates (Facebook, Instagram, Twitter) and save them into a single Excel workbook.

## Features
- Pull press releases directly from the official Hanwha newsroom API
- Aggregate social feed entries for Facebook and Instagram via the newsroom API
- (Optional) Scrape recent tweets from specified Hanwha-affiliated accounts using `snscrape`
- Export all datasets to an Excel file with dedicated sheets per channel

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Download one page of press releases, one page of social posts, skip Twitter
python src/main.py --press-pages 1 --social-pages 1 --no-twitter --output hanwha_updates.xlsx

# Include Twitter data (requires snscrape)
python src/main.py --press-pages 2 --social-pages 2 --twitter-user hanwha_group --twitter-limit 30
```

The resulting workbook contains three sheets:
- `PressReleases`
- `SocialMedia`
- `Twitter`

## Command Reference

| Flag | Description | Default |
| --- | --- | --- |
| `--press-pages` | Number of newsroom press pages to retrieve (12 items per page) | `1` |
| `--social-pages` | Number of social feed pages to collect | `1` |
| `--twitter-user` | Twitter username(s) without `@`; repeat the flag to add multiple accounts | `hanwha_official` |
| `--twitter-limit` | Max tweets per Twitter account | `20` |
| `--no-twitter` | Skip Twitter scraping and leave the Twitter sheet empty | _off_ |
| `--output` | Output Excel path | `hanwha_updates.xlsx` |
| `--log-level` | Logging verbosity (`DEBUG` .. `CRITICAL`) | `INFO` |

## Notes
- Twitter scraping relies on `snscrape`, which does not require API credentials but does need network access.
- When Twitter scraping is disabled (or `snscrape` is not installed), the exporter still generates the Excel file with the Twitter sheet left empty.
