# Step 3c: LLM-based Temporal Analysis of Self-Censorship
# Uses Claude API to analyse how creators' language on similar topics evolves
# over time, detecting self-censorship patterns by comparing early vs late transcripts.

#  this file is designed for the research report's purposes 
import sys
import os
import json
import csv
import time
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, DATA_INPUT_DIR

from dotenv import load_dotenv
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LLM_MODEL = "claude-sonnet-4-6"

# Project base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Transcript truncation limit (characters) to manage token usage
TRANSCRIPT_CHAR_LIMIT = 3000

# Rate limiting: seconds between API requests
REQUEST_INTERVAL = 2


def find_latest_raw_dir():
    """Find the latest archive run's raw directory, or fall back to data/raw."""
    archive_dir = os.path.join(BASE_DIR, "data", "archive")
    if os.path.isdir(archive_dir):
        runs = sorted([
            d for d in os.listdir(archive_dir)
            if d.startswith("run_") and os.path.isdir(os.path.join(archive_dir, d))
        ])
        if runs:
            raw_path = os.path.join(archive_dir, runs[-1], "raw")
            if os.path.isdir(raw_path):
                return raw_path

    # Fall back to configured DATA_RAW_DIR
    raw_path = os.path.join(BASE_DIR, DATA_RAW_DIR)
    if os.path.isdir(raw_path):
        return raw_path

    return None


def extract_video_id_from_url(url):
    """Extract a YouTube video ID from a URL."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def load_video_urls():
    """Read video_urls.csv and return a dict mapping channel_name -> list of video IDs."""
    csv_path = os.path.join(BASE_DIR, DATA_INPUT_DIR, "video_urls.csv")
    if not os.path.isfile(csv_path):
        print(f"ERROR: video_urls.csv not found at {csv_path}")
        return {}

    channels = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("url", "").strip()
            channel = row.get("channel_name", "").strip()
            if not url or not channel:
                continue
            video_id = extract_video_id_from_url(url)
            if video_id:
                channels.setdefault(channel, []).append(video_id)

    return channels


def load_metadata(raw_dir, video_id):
    """Load metadata.json for a given video ID."""
    meta_path = os.path.join(raw_dir, video_id, "metadata.json")
    if not os.path.isfile(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def load_transcript(raw_dir, video_id):
    """Load transcript.txt for a given video ID."""
    transcript_path = os.path.join(raw_dir, video_id, "transcript.txt")
    if not os.path.isfile(transcript_path):
        return None
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            return f.read()
    except IOError:
        return None


def parse_published_year(metadata):
    """Extract the publication year from metadata's published_at field."""
    published_at = metadata.get("published_at", "")
    if published_at and len(published_at) >= 4:
        try:
            return int(published_at[:4])
        except ValueError:
            pass
    return None


def select_video_pairs(raw_dir, video_ids):
    """
    For a channel's videos, select transcript pairs for temporal comparison.
    Returns list of tuples: (old_video_info, new_video_info)
    where each info dict has keys: video_id, title, year, transcript, metadata
    """
    # Load metadata and transcripts for all videos
    videos = []
    for vid_id in video_ids:
        meta = load_metadata(raw_dir, vid_id)
        if meta is None:
            continue
        transcript = load_transcript(raw_dir, vid_id)
        if not transcript or len(transcript.strip()) < 100:
            continue
        year = parse_published_year(meta)
        if year is None:
            continue
        videos.append({
            "video_id": vid_id,
            "title": meta.get("title", "Unknown"),
            "year": year,
            "published_at": meta.get("published_at", ""),
            "transcript": transcript,
            "metadata": meta,
        })

    if len(videos) < 2:
        return []

    # Sort by published_at date
    videos.sort(key=lambda v: v["published_at"])

    pairs = []

    # Pair 1: earliest vs latest
    pairs.append((videos[0], videos[-1]))

    # Pair 2: 2nd earliest vs 2nd latest (if 4+ videos available)
    if len(videos) >= 4:
        pairs.append((videos[1], videos[-2]))

    return pairs


def build_prompt(channel_name, old_video, new_video):
    """Build the analysis prompt for the Claude API."""
    transcript_old = old_video["transcript"][:TRANSCRIPT_CHAR_LIMIT]
    transcript_new = new_video["transcript"][:TRANSCRIPT_CHAR_LIMIT]

    prompt = f"""Compare these two transcripts from the same YouTube creator ({channel_name}).

Video 1: "{old_video['title']}" ({old_video['year']})
Transcript:
{transcript_old}

Video 2: "{new_video['title']}" ({new_video['year']})
Transcript:
{transcript_new}

Analyse:
1. Topic similarities between the two videos
2. Language differences — are sensitive/explicit words replaced with euphemisms or coded language in the newer video?
3. Tone shifts — is the newer video more cautious, hedged, or self-aware about content restrictions?
4. Specific word substitutions that suggest self-censorship (e.g., "unalive" instead of "kill")
5. Overall assessment: Does the evidence suggest the creator is self-censoring over time?

Provide your analysis in a structured format."""

    return prompt


def call_claude_api(client, prompt):
    """Send prompt to Claude API and return the response text."""
    message = client.messages.create(
        model=LLM_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    # Extract text from response content blocks
    response_text = ""
    for block in message.content:
        if hasattr(block, "text"):
            response_text += block.text
    return response_text


def parse_analysis_sections(response_text):
    """
    Parse the LLM response into structured fields.
    Returns dict with: topic_similarity, language_changes, censorship_indicators, overall_assessment
    """
    sections = {
        "topic_similarity": "",
        "language_changes": "",
        "censorship_indicators": "",
        "overall_assessment": "",
    }

    text = response_text

    # Try to extract numbered sections from the response
    # Section 1: Topic similarities
    match = re.search(
        r'(?:1\.\s*(?:Topic\s+similarities?|Topics?))(.*?)(?=\n\s*2\.|$)',
        text, re.DOTALL | re.IGNORECASE
    )
    if match:
        sections["topic_similarity"] = match.group(1).strip()

    # Section 2: Language differences
    match = re.search(
        r'(?:2\.\s*(?:Language\s+differences?|Language))(.*?)(?=\n\s*3\.|$)',
        text, re.DOTALL | re.IGNORECASE
    )
    if match:
        sections["language_changes"] = match.group(1).strip()

    # Section 4: Specific word substitutions / censorship indicators
    match = re.search(
        r'(?:4\.\s*(?:Specific\s+word|Word\s+substitutions?|Censorship))(.*?)(?=\n\s*5\.|$)',
        text, re.DOTALL | re.IGNORECASE
    )
    if match:
        sections["censorship_indicators"] = match.group(1).strip()

    # Section 5: Overall assessment
    match = re.search(
        r'(?:5\.\s*(?:Overall\s+assessment?|Overall))(.*?)$',
        text, re.DOTALL | re.IGNORECASE
    )
    if match:
        sections["overall_assessment"] = match.group(1).strip()

    # Fallback: if parsing failed, put full response in overall_assessment
    if not any(sections.values()):
        sections["overall_assessment"] = text.strip()

    return sections


def main():
    """Run LLM-based temporal analysis of self-censorship patterns."""
    print("=" * 70)
    print("Step 3c: LLM Temporal Analysis of Self-Censorship")
    print("=" * 70)

    # Check for API key
    if not ANTHROPIC_API_KEY:
        print("\nWARNING: ANTHROPIC_API_KEY not set in environment.")
        print("Skipping LLM analysis. Set the key in your .env file to enable this step.")
        print("  ANTHROPIC_API_KEY=your_api_key_here")
        return

    # Import anthropic SDK
    try:
        import anthropic
    except ImportError:
        print("\nERROR: anthropic package not installed.")
        print("Install it with: pip install anthropic")
        return

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Find raw data directory
    raw_dir = find_latest_raw_dir()
    if raw_dir is None:
        print("\nERROR: No raw data directory found.")
        print("Run Step 2 (batch extraction) first to download video data.")
        return
    print(f"\nUsing raw data from: {raw_dir}")

    # Load video URLs grouped by channel
    channel_videos = load_video_urls()
    if not channel_videos:
        print("\nERROR: No video URLs loaded. Check data/input/video_urls.csv")
        return
    print(f"Found {len(channel_videos)} channels in video_urls.csv")

    # Prepare output directories
    output_dir = os.path.join(BASE_DIR, DATA_OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    details_dir = os.path.join(output_dir, "llm_analysis_details")
    os.makedirs(details_dir, exist_ok=True)

    # CSV output
    csv_path = os.path.join(output_dir, "llm_temporal_analysis.csv")
    csv_rows = []

    total_pairs = 0
    total_analysed = 0

    for channel_name, video_ids in channel_videos.items():
        print(f"\n--- Channel: {channel_name} ({len(video_ids)} videos) ---")

        # Select video pairs for comparison
        pairs = select_video_pairs(raw_dir, video_ids)
        if not pairs:
            print(f"  Skipping: not enough videos with transcripts for temporal comparison")
            continue

        total_pairs += len(pairs)
        print(f"  Selected {len(pairs)} pair(s) for analysis")

        for pair_idx, (old_video, new_video) in enumerate(pairs, start=1):
            print(f"  Pair {pair_idx}: \"{old_video['title'][:50]}...\" ({old_video['year']}) "
                  f"vs \"{new_video['title'][:50]}...\" ({new_video['year']})")

            # Skip if both videos are from the same year
            if old_video["year"] == new_video["year"]:
                print(f"    Skipping: both videos from same year ({old_video['year']})")
                continue

            # Build and send prompt
            prompt = build_prompt(channel_name, old_video, new_video)

            try:
                print(f"    Sending to Claude API...", end="", flush=True)
                response_text = call_claude_api(client, prompt)
                print(" done")
                total_analysed += 1
            except Exception as e:
                print(f" failed: {e}")
                continue

            # Parse the response into structured sections
            sections = parse_analysis_sections(response_text)

            # Build CSV row
            row = {
                "channel": channel_name,
                "video_id_old": old_video["video_id"],
                "video_id_new": new_video["video_id"],
                "title_old": old_video["title"],
                "title_new": new_video["title"],
                "year_old": old_video["year"],
                "year_new": new_video["year"],
                "topic_similarity": sections["topic_similarity"],
                "language_changes": sections["language_changes"],
                "censorship_indicators": sections["censorship_indicators"],
                "overall_assessment": sections["overall_assessment"],
            }
            csv_rows.append(row)

            # Save detailed JSON output
            detail_filename = re.sub(r'[^\w\-]', '_', channel_name) + f"_pair_{pair_idx}.json"
            detail_path = os.path.join(details_dir, detail_filename)
            detail_data = {
                "channel": channel_name,
                "pair_index": pair_idx,
                "video_old": {
                    "video_id": old_video["video_id"],
                    "title": old_video["title"],
                    "year": old_video["year"],
                    "published_at": old_video["published_at"],
                },
                "video_new": {
                    "video_id": new_video["video_id"],
                    "title": new_video["title"],
                    "year": new_video["year"],
                    "published_at": new_video["published_at"],
                },
                "prompt": prompt,
                "raw_response": response_text,
                "parsed_sections": sections,
            }
            with open(detail_path, "w", encoding="utf-8") as f:
                json.dump(detail_data, f, indent=2, ensure_ascii=False)
            print(f"    Saved detail: {detail_filename}")

            # Rate limiting
            time.sleep(REQUEST_INTERVAL)

    # Write CSV output
    if csv_rows:
        fieldnames = [
            "channel", "video_id_old", "video_id_new",
            "title_old", "title_new", "year_old", "year_new",
            "topic_similarity", "language_changes",
            "censorship_indicators", "overall_assessment",
        ]
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"\nCSV output saved to: {csv_path}")
    else:
        print("\nNo analyses completed — no CSV output generated.")

    print(f"\n{'=' * 70}")
    print(f"LLM Analysis Complete")
    print(f"  Channels processed: {len(channel_videos)}")
    print(f"  Pairs identified:   {total_pairs}")
    print(f"  Pairs analysed:     {total_analysed}")
    print(f"  Output CSV:         {csv_path}")
    print(f"  Detail JSONs:       {details_dir}/")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
