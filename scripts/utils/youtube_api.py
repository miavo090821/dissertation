# YouTube API Helper Functions
# Handles all interactions with YouTube Data API v3 and youtube-transcript-api


import re
import json
import os
from datetime import datetime
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

def get_video_id(url: str) -> str:
def get_youtube_client(api_key: str):

def get_video_metadata(api_key: str, video_id: str) -> dict:

def get_channel_info(api_key: str, channel_id: str) -> dict:

def get_video_transcript(video_id: str, max_retries: int = 3) -> tuple:

def get_video_comments(api_key: str, video_id: str, max_comments: int = 200) -> list:


def parse_duration(duration_str: str) -> int:

def format_duration(seconds: int) -> str:
 
 
def save_video_data(output_dir: str, video_id: str, metadata: dict, 
                    transcript_text: str, transcript_segments: list, 
                    comments: list) -> None:   