import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('script_generator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NotionVideoScriptGenerator:
    def __init__(self, notion_token: str, openai_api_key: str, database_id: str):
        """
        Initialize the script generator with API credentials
        
        Args:
            notion_token: Your Notion integration token
            openai_api_key: Your OpenAI API key
            database_id: Your Notion database ID
        """
        self.notion_token = notion_token
        self.database_id = database_id
        self.notion_headers = {
            "Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Track processed videos to avoid duplicates
        self.processed_videos = set()
        
    def get_videos_for_scripting(self) -> List[Dict]:
        """
        Query Notion database for videos with status 'Scripting'
        """
        url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        
        payload = {
            "filter": {
                "property": "Status",
                "select": {
                    "equals": "Scripting"
                }
            }
        }
        
        try:
            response = requests.post(url, headers=self.notion_headers, json=payload)
            response.raise_for_status()
            
            results = response.json().get('results', [])
            logger.info(f"Found {len(results)} videos with 'Scripting' status")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Notion database: {e}")
            return []
    
    def extract_video_info(self, page: Dict) -> Optional[Dict]:
        """
        Extract video title and other relevant info from Notion page
        """
        try:
            page_id = page['id']
            properties = page['properties']
            
            # Extract title (adjust property name as needed)
            title_property = properties.get('Video Title')
            if not title_property:
                logger.warning(f"No title found for page {page_id}")
                return None
                
            if title_property['type'] == 'title':
                title = ''.join([text['plain_text'] for text in title_property['title']])
            elif title_property['type'] == 'rich_text':
                title = ''.join([text['plain_text'] for text in title_property['rich_text']])
            else:
                title = str(title_property)
            
            # Extract additional context if available
            description = ""
            if 'Video Description' in properties:
                desc_prop = properties['Video Description']
                if desc_prop['type'] == 'rich_text' and desc_prop['rich_text']:
                    description = ''.join([text['plain_text'] for text in desc_prop['rich_text']])
            
            return {
                'page_id': page_id,
                'title': title,
                'description': description
            }
            
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return None
    
    def generate_script_with_openai(self, title: str, description: str = "") -> str:
        """
        Generate a detailed video script using OpenAI with markdown formatting
        """
        # Create a comprehensive prompt for script generation with markdown
        prompt = f"""
        Create a detailed, engaging YouTube video script for the following video:

        Title: {title}
        {f"Additional Context: {description}" if description else ""}

        Please structure the script with markdown formatting using the following sections:
        
        # Video Script: {title}
        
        ## 🎯 Hook (0-15 seconds)
        [Write an attention-grabbing opening that hooks viewers immediately]
        
        ## 👋 Introduction & Welcome
        [Channel introduction and video overview]
        
        ## 📋 Main Content
        ### Section 1: [Topic Name]
        [Main content broken into clear subsections]
        
        ### Section 2: [Topic Name]
        [Continue with additional sections as needed]
        
        ### Section 3: [Topic Name]
        [Add more sections based on the topic]
        
        ## 📞 Call-to-Action
        [Subscribe, like, comment reminders]
        
        ## 👋 Outro
        [Closing remarks and next video teasers]
        
        ---
        
        **Formatting Guidelines:**
        - Use markdown headers (##, ###) for sections
        - Use **bold** for emphasis on key points
        - Use [brackets] for visual/B-roll suggestions
        - Include natural conversation flow
        - Add retention hooks between sections
        - Make it conversational and engaging
        - Target 8-12 minutes of speaking content
        - Include specific talking points, not just outlines

        **Content Requirements:**
        - Make it specific to the topic, not generic
        - Include concrete examples and actionable advice
        - Add personal touches and storytelling elements
        - Include viewer engagement questions
        - Provide clear value propositions
        - Make some jokes or light-hearted comments to keep it fun
        - Use a friendly, approachable tone
        - Give code snippets or examples for programming topics

        Generate the complete script with full dialogue, not just bullet points or outlines.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert YouTube script writer who creates engaging, well-structured video scripts with proper markdown formatting that maximize viewer retention and engagement. Always write complete dialogue and full scripts, never just outlines or bullet points."
                    },
                    {
                        "role": "system", 
                        "content": "I have a YouTube channel named 'ADev Tutorials' that focuses on Web Development, Programming and AI. Please tailor the script to fit this niche."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.7
            )
            
            script = response.choices[0].message.content
            logger.info(f"Generated markdown script for '{title}' ({len(script)} characters)")
            logger.info(f"Script for '{title}'\n{script}")
            return script
            
        except Exception as e:
            logger.error(f"Error generating script with OpenAI: {e}")
            return f"# Error Generating Script\n\n**Error:** {str(e)}\n\nPlease check your OpenAI API key and try again."
    
    def update_notion_page_with_script(self, page_id: str, script: str) -> bool:
        """
        Update the Notion page with the generated script as page content
        """
        # First, update the page properties (status and timestamp)
        properties_url = f"https://api.notion.com/v1/pages/{page_id}"
        properties_payload = {
            "properties": {
                "Status": {  # Change status to indicate script is ready
                    "select": {
                        "name": "Review"  # Adjust status name as needed
                    }
                },
                "Script Generated": { 
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                }
            }
        }
        
        try:
            response = requests.patch(properties_url, headers=self.notion_headers, json=properties_payload)
            response.raise_for_status()
            logger.info(f"Updated page properties for {page_id}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating page properties: {e}")
            # Continue anyway to add the script content
        
        # Add the script as page content (blocks)
        return self.add_script_as_page_content(page_id, script)
    
    def add_script_as_page_content(self, page_id: str, script: str) -> bool:
        """
        Add script content as markdown-formatted blocks to the page content
        """
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        
        # Clear existing content first (optional - remove if you want to keep existing content)
        # self.clear_page_content(page_id)
        
        # Parse the script and convert to Notion blocks with markdown formatting
        blocks = self.convert_script_to_notion_blocks(script)
        
        # Add blocks in batches (Notion has a limit of 100 blocks per request)
        batch_size = 100
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i + batch_size]
            payload = {"children": batch}
            
            try:
                response = requests.patch(url, headers=self.notion_headers, json=payload)
                response.raise_for_status()
                logger.info(f"Added batch {i//batch_size + 1} of script blocks to page {page_id}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error adding script blocks batch {i//batch_size + 1}: {e}")
                return False
        
        logger.info(f"Successfully added complete script as page content to {page_id}")
        return True
    
    def convert_script_to_notion_blocks(self, script: str) -> List[Dict]:
        """
        Convert the script text to properly formatted Notion blocks with markdown support
        """
        blocks = []
        lines = script.split('\n')
        
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines but use them to break paragraphs
            if not line:
                if current_paragraph:
                    # Add the accumulated paragraph
                    paragraph_text = ' '.join(current_paragraph)
                    if paragraph_text:
                        blocks.append(self.create_paragraph_block(paragraph_text))
                    current_paragraph = []
                continue
            
            # Handle different markdown elements
            if line.startswith('# '):
                # Add any accumulated paragraph first
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    blocks.append(self.create_paragraph_block(paragraph_text))
                    current_paragraph = []
                # Add heading 1
                blocks.append(self.create_heading_block(line[2:], 1))
                
            elif line.startswith('## '):
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    blocks.append(self.create_paragraph_block(paragraph_text))
                    current_paragraph = []
                blocks.append(self.create_heading_block(line[3:], 2))
                
            elif line.startswith('### '):
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    blocks.append(self.create_paragraph_block(paragraph_text))
                    current_paragraph = []
                blocks.append(self.create_heading_block(line[4:], 3))
                
            elif line.startswith('- ') or line.startswith('* '):
                # Handle bullet points
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    blocks.append(self.create_paragraph_block(paragraph_text))
                    current_paragraph = []
                blocks.append(self.create_bullet_block(line[2:]))
                
            elif line.startswith('1. ') or any(line.startswith(f'{i}. ') for i in range(1, 10)):
                # Handle numbered lists
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    blocks.append(self.create_paragraph_block(paragraph_text))
                    current_paragraph = []
                # Extract the text after the number
                text = line.split('. ', 1)[1] if '. ' in line else line
                blocks.append(self.create_numbered_block(text))
                
            elif line.startswith('**') and line.endswith('**'):
                # Handle bold text as a separate paragraph
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    blocks.append(self.create_paragraph_block(paragraph_text))
                    current_paragraph = []
                blocks.append(self.create_paragraph_block(line, bold=True))
                
            else:
                # Regular text - accumulate into paragraph
                current_paragraph.append(line)
        
        # Add any remaining paragraph
        if current_paragraph:
            paragraph_text = ' '.join(current_paragraph)
            blocks.append(self.create_paragraph_block(paragraph_text))
        
        # Add a final separator
        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })
        
        return blocks
    
    def create_heading_block(self, text: str, level: int) -> Dict:
        """Create a heading block"""
        heading_type = f"heading_{level}"
        return {
            "object": "block",
            "type": heading_type,
            heading_type: {
                "rich_text": [self.create_rich_text(text)]
            }
        }
    
    def create_paragraph_block(self, text: str, bold: bool = False) -> Dict:
        """Create a paragraph block with optional formatting"""
        # Handle text that might contain markdown formatting
        rich_text = self.parse_inline_formatting(text, bold)
        
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": rich_text
            }
        }
    
    def create_bullet_block(self, text: str) -> Dict:
        """Create a bulleted list item block"""
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [self.create_rich_text(text)]
            }
        }
    
    def create_numbered_block(self, text: str) -> Dict:
        """Create a numbered list item block"""
        return {
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [self.create_rich_text(text)]
            }
        }
    
    def create_rich_text(self, text: str, bold: bool = False, italic: bool = False, code: bool = False) -> Dict:
        """Create a rich text object with formatting"""
        annotations = {}
        if bold:
            annotations["bold"] = True
        if italic:
            annotations["italic"] = True
        if code:
            annotations["code"] = True
        
        rich_text_obj = {
            "type": "text",
            "text": {"content": text[:2000]}  # Notion's character limit per text object
        }
        
        if annotations:
            rich_text_obj["annotations"] = annotations
            
        return rich_text_obj
    
    def parse_inline_formatting(self, text: str, force_bold: bool = False) -> List[Dict]:
        """Parse inline markdown formatting like **bold** and *italic*"""
        if force_bold:
            return [self.create_rich_text(text.replace('**', ''), bold=True)]
        
        # Simple parsing for basic formatting
        # This is a basic implementation - you can enhance it for more complex formatting
        parts = []
        current_text = text
        
        # Handle [visual cues] as italic text
        import re
        visual_cues = re.findall(r'\[([^\]]+)\]', current_text)
        if visual_cues:
            # Split text and format visual cues
            split_text = re.split(r'\[([^\]]+)\]', current_text)
            for i, part in enumerate(split_text):
                if part in visual_cues:
                    parts.append(self.create_rich_text(f"[{part}]", italic=True))
                elif part.strip():
                    parts.append(self.create_rich_text(part))
        else:
            # Handle **bold** text
            if '**' in current_text:
                bold_parts = current_text.split('**')
                for i, part in enumerate(bold_parts):
                    if part.strip():
                        is_bold = i % 2 == 1  # Every other part is bold
                        parts.append(self.create_rich_text(part, bold=is_bold))
            else:
                parts.append(self.create_rich_text(current_text))
        
        return parts if parts else [self.create_rich_text(text)]
    
    def clear_page_content(self, page_id: str) -> bool:
        """
        Clear existing page content (optional - uncomment the call above if needed)
        """
        # Get existing blocks
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        
        try:
            response = requests.get(blocks_url, headers=self.notion_headers)
            response.raise_for_status()
            blocks = response.json().get('results', [])
            
            # Delete each block
            for block in blocks:
                delete_url = f"https://api.notion.com/v1/blocks/{block['id']}"
                requests.delete(delete_url, headers=self.notion_headers)
            
            logger.info(f"Cleared {len(blocks)} existing blocks from page {page_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error clearing page content: {e}")
            return False
    
    def process_videos(self):
        """
        Main method to process videos and generate scripts
        """
        videos = self.get_videos_for_scripting()
        
        for video_data in videos:
            video_info = self.extract_video_info(video_data)
            if not video_info:
                continue
                
            page_id = video_info['page_id']
            
            # Skip if already processed in this session
            if page_id in self.processed_videos:
                continue
                
            title = video_info['title']
            description = video_info['description']
            
            logger.info(f"Processing video: {title}")
            
            # Generate script
            script = self.generate_script_with_openai(title, description)

            # Update Notion page
            if self.update_notion_page_with_script(page_id, script):
                self.processed_videos.add(page_id)
                logger.info(f"✅ Successfully processed: {title}")
            else:
                logger.error(f"❌ Failed to process: {title}")
    
    def run_continuously(self, check_interval: int = 300):
        """
        Run the script continuously, checking for new videos every few minutes
        
        Args:
            check_interval: Time in seconds between checks (default: 5 minutes)
        """
        logger.info(f"Starting continuous monitoring (checking every {check_interval} seconds)")
        
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
    Main function to run the script
    """
    # Configuration - replace with your actual values
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
    
    # Validate configuration
    if not all([NOTION_TOKEN, OPENAI_API_KEY, DATABASE_ID]):
        print("❌ Please set your environment variables:")
        print("   - NOTION_TOKEN")
        print("   - OPENAI_API_KEY") 
        print("   - NOTION_DATABASE_ID")
        print("\nOr update the values directly in the script.")
        return
    
    # Initialize and run the generator
    generator = NotionVideoScriptGenerator(
        notion_token=NOTION_TOKEN,
        openai_api_key=OPENAI_API_KEY,
        database_id=DATABASE_ID
    )
    
    logger.info("🚀 YouTube Script Generator Started!")
    logger.info("Monitoring your Notion database for videos with 'scripting' status...")
    logger.info("Press Ctrl+C to stop")

    # Run once immediately, then continuously
    generator.process_videos()
    # generator.run_continuously(check_interval=300)  # Check every 5 minutes

if __name__ == "__main__":
    main()