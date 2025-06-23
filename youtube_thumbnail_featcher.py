import os
import time
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('youtube_thumbnail_fetcher.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class YouTubeThumbnailFetcher:
    def __init__(self, notion_token: str, database_id: str):
        """
        Initialize the YouTube thumbnail fetcher
        
        Args:
            notion_token: Your Notion integration token
            database_id: Your Notion database ID
        """
        self.notion_token = notion_token
        self.database_id = database_id
        self.notion_headers = {
            "Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        # Track processed videos to avoid duplicates
        self.processed_videos = set()
        
    def get_videos_with_youtube_urls(self) -> List[Dict]:
        """
        Query Notion database for videos that have YouTube URLs but no thumbnails yet
        """
        url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        
        # Query for videos that have YouTube URLs
        payload = {
            "filter": {
                "and": [
                    {
                        "property": "URL",
                        "rich_text": {
                            "is_not_empty": True
                        }
                    },
                    {
                        "property": "Thumbnail URL",
                        "rich_text": {
                            "is_empty": True
                        }
                    }
                ]
            }
        }
        
        try:
            response = requests.post(url, headers=self.notion_headers, json=payload)
            response.raise_for_status()
            
            results = response.json().get('results', [])
            logger.info(f"Found {len(results)} videos with YouTube URLs")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Notion database: {e}")
            return []
    
    def extract_video_info(self, page: Dict) -> Optional[Dict]:
        """
        Extract video information including YouTube URL and check for existing thumbnails
        """
        try:
            page_id = page['id']
            properties = page['properties']
            
            # Extract title
            title_property = properties.get('Video Title') or properties.get('Name')
            if not title_property:
                logger.warning(f"No title found for page {page_id}")
                return None
                
            if title_property['type'] == 'title':
                title = ''.join([text['plain_text'] for text in title_property['title']])
            elif title_property['type'] == 'rich_text':
                title = ''.join([text['plain_text'] for text in title_property['rich_text']])
            else:
                title = str(title_property)
            
            # Extract YouTube URL
            youtube_url_property = properties.get('YouTube URL') or properties.get('URL')
            if not youtube_url_property:
                logger.warning(f"No YouTube URL found for page {page_id}")
                return None
            
            youtube_url = ""
            if youtube_url_property['type'] == 'url':
                youtube_url = youtube_url_property['url'] or ""
            elif youtube_url_property['type'] == 'rich_text':
                youtube_url = ''.join([text['plain_text'] for text in youtube_url_property['rich_text']])
            
            if not youtube_url:
                logger.warning(f"Empty YouTube URL for page {page_id}")
                return None
            
            # Check if this is a valid YouTube URL
            video_id = self.extract_youtube_video_id(youtube_url)
            if not video_id:
                logger.warning(f"Invalid YouTube URL for page {page_id}: {youtube_url}")
                return None
            
            return {
                'page_id': page_id,
                'title': title,
                'youtube_url': youtube_url,
                'video_id': video_id
            }
            
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return None
    
    def extract_youtube_video_id(self, url: str) -> Optional[str]:
        """
        Extract YouTube video ID from various YouTube URL formats
        """
        # Common YouTube URL patterns
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Try parsing as URL
        try:
            parsed_url = urlparse(url)
            if 'youtube.com' in parsed_url.netloc:
                if parsed_url.path == '/watch':
                    return parse_qs(parsed_url.query).get('v', [None])[0]
                elif parsed_url.path.startswith('/embed/'):
                    return parsed_url.path.split('/embed/')[1].split('?')[0]
            elif 'youtu.be' in parsed_url.netloc:
                return parsed_url.path[1:].split('?')[0]
        except:
            pass
        
        return None
    
    def get_youtube_thumbnail_urls(self, video_id: str) -> Dict[str, str]:
        """
        Get different quality YouTube thumbnail URLs
        """
        base_url = f"https://img.youtube.com/vi/{video_id}"
        
        thumbnails = {
            "maxresdefault": f"{base_url}/maxresdefault.jpg",  # 1280x720
            "sddefault": f"{base_url}/sddefault.jpg",          # 640x480
            "hqdefault": f"{base_url}/hqdefault.jpg",          # 480x360
            "mqdefault": f"{base_url}/mqdefault.jpg",          # 320x180
            "default": f"{base_url}/default.jpg"               # 120x90
        }
        
        return thumbnails
    
    def verify_thumbnail_exists(self, url: str) -> bool:
        """
        Verify if a thumbnail URL actually exists and returns a valid image
        """
        try:
            response = requests.head(url, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_best_available_thumbnails(self, video_id: str) -> List[Tuple[str, str]]:
        """
        Get the best available thumbnail URLs for a video
        Returns list of (quality_name, url) tuples
        """
        thumbnail_urls = self.get_youtube_thumbnail_urls(video_id)
        available_thumbnails = []
        
        # Check thumbnails in order of preference (highest quality first)
        quality_order = ["maxresdefault", "sddefault", "hqdefault", "mqdefault", "default"]
        
        for quality in quality_order:
            url = thumbnail_urls[quality]
            if self.verify_thumbnail_exists(url):
                available_thumbnails.append((quality.replace('default', '').upper() or 'DEFAULT', url))
                logger.info(f"✅ Found {quality} thumbnail for video {video_id}")
            else:
                logger.debug(f"❌ {quality} thumbnail not available for video {video_id}")
        
        return available_thumbnails
    
    def update_thumbnail_url_property(self, page_id: str, thumbnail_url: str) -> bool:
        """
        Update the Notion page's 'Thumbnail URL' property with the given URL
        """
        url = f"https://api.notion.com/v1/pages/{page_id}"
        payload = {
            "properties": {
                "Thumbnail URL": {
                    "url": thumbnail_url
                }
            }
        }
        try:
            response = requests.patch(url, headers=self.notion_headers, json=payload)
            response.raise_for_status()
            logger.info(f"✅ Updated Thumbnail URL property for page {page_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating Thumbnail URL property: {e}")
            return False
    
    
    def process_videos(self):
        """
        Main method to process videos and fetch YouTube thumbnails
        (Only updates 'Thumbnail URL' property, does not add image blocks)
        """
        videos = self.get_videos_with_youtube_urls()

        processed_count = 0
        skipped_count = 0

        for video_data in videos:
            video_info = self.extract_video_info(video_data)
            if not video_info:
                continue

            page_id = video_info['page_id']
            title = video_info['title']
            video_id = video_info['video_id']
            youtube_url = video_info['youtube_url']

            # Skip if already processed in this session
            if page_id in self.processed_videos:
                continue

            logger.info(f"Processing: {title}")
            logger.info(f"YouTube URL: {youtube_url}")
            logger.info(f"Video ID: {video_id}")

            # Get available thumbnails
            thumbnails = self.get_best_available_thumbnails(video_id)
            if not thumbnails:
                logger.error(f"❌ No thumbnails found for '{title}' (Video ID: {video_id})")
                continue

            # Use the first (best) available thumbnail
            best_thumbnail_url = thumbnails[0][1]

            # Update the 'Thumbnail URL' property on the Notion page
            if self.update_thumbnail_url_property(page_id, best_thumbnail_url):
                processed_count += 1
                logger.info(f"✅ Successfully processed '{title}' - Added thumbnail URL")
            else:
                logger.error(f"❌ Failed to update Thumbnail URL for '{title}'")

            self.processed_videos.add(page_id)
            time.sleep(1)

        logger.info(f"📊 Processing complete: {processed_count} processed, {skipped_count} skipped")

    
    def run_continuously(self, check_interval: int = 600):
        """
        Run the script continuously, checking for new videos every few minutes
        
        Args:
            check_interval: Time in seconds between checks (default: 10 minutes)
        """
        logger.info(f"Starting continuous YouTube thumbnail monitoring (checking every {check_interval} seconds)")
        
        while True:
            try:
                self.process_videos()
                logger.info(f"Waiting {check_interval} seconds before next check...")
                time.sleep(check_interval)
            except KeyboardInterrupt:
                logger.info("Script stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

def main():
    """
    Main function to run the YouTube thumbnail fetcher
    """
    # Configuration - replace with your actual values
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
    
    # Validate configuration
    if not all([NOTION_TOKEN, DATABASE_ID]):
        print("❌ Please set your environment variables:")
        print("   - NOTION_TOKEN")
        print("   - NOTION_DATABASE_ID")
        print("\nOr update the values directly in the script.")
        return
    
    # Initialize and run the fetcher
    fetcher = YouTubeThumbnailFetcher(
        notion_token=NOTION_TOKEN,
        database_id=DATABASE_ID
    )
    
    logger.info("🚀 YouTube Thumbnail Fetcher Started!")
    logger.info("Features:")
    logger.info("  📺 Fetches original YouTube thumbnails")
    logger.info("  🔍 Checks for existing thumbnails to avoid duplicates")
    logger.info("  📊 Multiple quality options (Max, SD, HQ, MQ, Default)")
    logger.info("  ✅ Updates page status when complete")
    logger.info("\nMonitoring your Notion database for videos with YouTube URLs...")
    logger.info("Press Ctrl+C to stop")

    fetcher.run_continuously(check_interval=600)  # Check every 10 minutes

if __name__ == "__main__":
    main()