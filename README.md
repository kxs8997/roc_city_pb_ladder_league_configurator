# ROC City Pickleball - Ladder League Configurator

A Windows desktop application for managing 4-court pickleball ladder leagues with intelligent scheduling to prevent repetitive matchups and court assignments.

## Features

- **Player Management**: Add/remove players easily
- **Smart Scheduling**: Algorithm ensures:
  - Players don't get stuck on the same court repeatedly
  - Players don't play the same opponents too frequently
  - Fair distribution across all 4 courts
- **Statistics Tracking**: View player court usage and matchup frequency
- **Persistent Data**: Automatically saves all data between sessions

## Installation for Club PC

### Option 1: Use Pre-built Executable (Easiest)
1. Copy the `ROC_City_Ladder_League.exe` file to the club PC
2. Copy `RocCityPickleball_4k.png` to the same folder
3. Double-click the `.exe` to run - no installation needed!

### Option 2: Build from Source
1. Install Python 3.10+ from python.org
2. Open Command Prompt in this folder
3. Run: `pip install -r requirements.txt`
4. Run: `build_exe.bat`
5. Find the executable in the `dist` folder

## How to Use

### Adding Players
1. Go to the **Players** tab
2. Enter player name and click "Add Player"
3. Repeat for all league participants (minimum 8 players needed)

### Generating Rounds
1. Go to the **Schedule Round** tab
2. Click "Generate New Round"
3. The app will assign 4 players to each of the 4 courts
4. Teams are automatically created (2v2 format)

### Viewing Statistics
1. Go to the **Statistics** tab
2. Click "Refresh Statistics" to see:
   - How many times each player has played on each court
   - How many times players have faced each other
   - Total rounds played per player

### Resetting History
- If you want to start a new season, use "Reset Match History" in the Players tab
- This clears court and matchup history but keeps your player list

## How the Ladder League Works

This tool implements a **rotation-based ladder league** system:

1. **4 Courts, 16 Players**: Each round fills all 4 courts with 4 players each (2v2 doubles)
2. **Smart Rotation**: The algorithm tracks:
   - Which courts each player has used
   - Who has played together/against each other
3. **Fair Distribution**: Players are assigned to minimize:
   - Repeating the same court
   - Facing the same opponents repeatedly
4. **Flexible Participation**: If you have more than 16 players, some will sit out each round (rotated fairly)

## Data Storage

All data is saved automatically to `ladder_league_data.json` in the same folder as the application. This file contains:
- Player list
- Match history
- Court usage history

**Backup Tip**: Periodically copy this JSON file to preserve your league data!

## System Requirements

- Windows 7 or later
- No other software required (if using the .exe)

## Troubleshooting

**"Need at least 8 players"**: Add more players to the roster (minimum 2 per court × 4 courts)

**Logo not showing**: Make sure `RocCityPickleball_4k.png` is in the same folder as the executable

**Data lost**: Check for `ladder_league_data.json` in the application folder - restore from backup if needed

## Support

For issues or questions, contact the developer who set this up for your club.
