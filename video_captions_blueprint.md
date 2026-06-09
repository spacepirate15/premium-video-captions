# Video Captions Workspace Blueprint

## 1. Workspace Objective
This workspace is strictly dedicated to processing raw videos by adding premium, highly-engaging captions for social media platforms. 

## 2. Folder Structure
When initializing this workspace, the agent must create the following directory tree:

```text
/captions
├── 01-raw-videos/          # Drop your unedited videos here
├── 02-processed-videos/    # Final output videos with captions
├── 03-assets/              # Any fonts, branding elements, or overlays
├── 04-scripts/             # Python/FFmpeg scripts for caption generation
└── logs/                   # Processing logs and agent notes
```

## 3. Agent Execution Workflow
When a new video is placed in `01-raw-videos/`, the agent should follow these steps:
1. **Transcribe:** Extract audio and generate a precise transcript with timestamps (e.g., using Whisper).
2. **Format:** Break the text into short, punchy segments (1-3 words per screen) for high retention.
3. **Burn Captions:** Render the video with burned-in subtitles into `02-processed-videos/`.

## 4. Premium Caption Styling & Safe Zones
The agent must apply the following styling rules when generating captions to ensure a premium look:
- **Font:** Use bold, modern, and readable sans-serif fonts (e.g., Montserrat, TheBoldFont, Arial Black).
- **Styling:** 
  - White text with a solid black drop-shadow or soft black background stroke for maximum contrast.
  - Highlight key action words or numbers in brand colors (e.g., vibrant yellow or neon green).
- **Animations:** Pop-in or scale-up effects on word reveal (if supported by the processing script), otherwise clean cut-to-cut word reveals.
- **Safe Zones:** 
  - Position the text in the center-bottom of the screen (around 20-30% from the bottom).
  - Ensure the text does not overlap with native social media UI elements (mute button, timeline at the bottom, or forward buttons). Keep a 15% margin on the left and right edges.

## 5. Initialization Command
*Prompt to give the agent in the new workspace:*
> "Hello! Please read `video_captions_blueprint.md`. Ensure the folder structure defined in the file is present. Once done, wait for me to drop a video into `01-raw-videos/` and then apply the premium caption styling as outlined."
