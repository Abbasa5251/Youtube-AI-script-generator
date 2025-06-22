# YouTube Script Generator 🎬

An automated Python script that monitors your Notion database and generates detailed YouTube video scripts using OpenAI's GPT when you change a video's status to "scripting".

## ✨ Features

-   **Automated Monitoring**: Continuously monitors your Notion database for videos marked as "scripting"
-   **AI-Powered Scripts**: Uses OpenAI GPT-4 to generate detailed, engaging video scripts
-   **Markdown Formatting**: Creates beautifully formatted scripts with proper structure
-   **Smart Content Parsing**: Converts markdown to properly formatted Notion blocks
-   **Error Handling**: Robust error handling with detailed logging
-   **Batch Processing**: Handles multiple videos efficiently

## 🔧 Prerequisites

Before you begin, ensure you have:

-   Python 3.7 or higher
-   A Notion account with a database for video ideas
-   An OpenAI API account with credits
-   Basic familiarity with Python and command line

## 📦 Installation

### 1. Clone or Download the Script

Save the `main.py` file to your desired directory.

### 2. Install Required Dependencies

```bash
pip install openai requests python-dotenv
```

Or create a `requirements.txt` file:

```txt
openai>=1.90.0
python-dotenv>=1.1.0
requests>=2.32.4
```

Then install:

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

### 1. Environment Variables

Create a `.env` file in the same directory as your script:

```env
NOTION_TOKEN=your_notion_integration_token_here
OPENAI_API_KEY=your_openai_api_key_here
NOTION_DATABASE_ID=your_notion_database_id_here
```

### 2. Get Your Notion Integration Token

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Fill in the integration details:
    - Name: "YouTube Script Generator"
    - Logo: Optional
    - Associated workspace: Select your workspace
4. Click "Submit"
5. Copy the "Internal Integration Token"
6. Add it to your `.env` file

### 3. Get Your OpenAI API Key

1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Click "Create new secret key"
3. Copy the key and add it to your `.env` file
4. Ensure you have credits in your OpenAI account

### 4. Get Your Notion Database ID

From your Notion database URL:

```
https://www.notion.so/your-workspace/DATABASE_ID?v=view_id
```

The `DATABASE_ID` is the 32-character string after your workspace name.

## 🗄️ Notion Database Setup

### Required Properties

Create a Notion database with these properties:

| Property Name         | Type      | Description                       | Required    |
| --------------------- | --------- | --------------------------------- | ----------- |
| **Title** or **Name** | Title     | Video title/name                  | ✅ Yes      |
| **Status**            | Select    | Video status                      | ✅ Yes      |
| **Description**       | Rich Text | Additional context                | ❌ Optional |
| **Script_Generated**  | Date      | Timestamp when script was created | ❌ Optional |

### Status Property Options

Add these options to your Status select property:

-   `scripting` - Triggers script generation
-   `review` - Set automatically after script generation
-   `idea` - For initial video ideas
-   `published` - For completed videos
-   `archived` - For unused ideas

### Share Database with Integration

1. Open your Notion database
2. Click the "Share" button (top right)
3. Click "Invite"
4. Search for your integration name (e.g., "YouTube Script Generator")
5. Select it and click "Invite"

## 🚀 Usage

### Running the Script

#### Option 1: One-time Run

```bash
python main.py
```

#### Option 2: Continuous Monitoring (Recommended)

The script runs continuously by default, checking every 5 minutes:

```bash
python main.py
```

### Workflow

1. **Add Video Ideas**: Add new video titles to your Notion database
2. **Trigger Script Generation**: Change the status to "scripting"
3. **Automatic Processing**: The script detects the change and generates a script
4. **Review Results**: Check your Notion page for the generated script
5. **Status Update**: Status automatically changes to "review"

### Stopping the Script

Press `Ctrl + C` to stop the monitoring script.

## ❓ FAQ

### Q: How much does it cost to run?

**A**: Costs depend on OpenAI usage. GPT-4 costs ~$0.03-0.06 per script, GPT-3.5-turbo costs ~$0.002-0.004 per script.

### Q: Can I run this on a server?

**A**: Yes! The script is designed for continuous operation. Consider using a process manager like `supervisord` or `systemd`.

### Q: How long are the generated scripts?

**A**: Scripts are typically 2000-4000 words, designed for 8-12 minutes of speaking content.

### Q: Can I modify the script structure?

**A**: Absolutely! Edit the prompt in `generate_script_with_openai()` to customize the output format.

### Q: What if my database has different property names?

**A**: Update the property names in the code to match your database schema.

### Q: Can I process multiple videos at once?

**A**: Yes, the script processes all videos with "scripting" status in each run.

## 📊 Performance Tips

### Optimize Costs

-   Use GPT-3.5-turbo instead of GPT-4 for 90% cost reduction
-   Increase check interval to reduce API calls
-   Add more specific context to reduce token usage

### Improve Quality

-   Add detailed descriptions to your video ideas
-   Customize the prompt for your channel's style
-   Review and refine generated scripts

### Scale Operations

-   Use a database template for consistent property names
-   Set up automated backups of your scripts
-   Consider using Notion's formula properties for additional automation

## 🤝 Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

### Development Setup

1. Fork the repository
2. Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4. Make your changes
5. Test thoroughly
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Useful Links

-   [Notion API Documentation](https://developers.notion.com/)
-   [OpenAI API Documentation](https://platform.openai.com/docs)
-   [Python Requests Documentation](https://docs.python-requests.org/)

---

**Happy Scripting! 🎬✨**

_This tool is designed to enhance your YouTube content creation workflow by automating the script generation process. Remember to review and personalize the generated scripts to match your unique voice and style._
