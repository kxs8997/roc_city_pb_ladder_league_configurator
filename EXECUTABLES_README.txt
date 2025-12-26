================================================================================
ROC CITY PICKLEBALL LADDER LEAGUE - EXECUTABLE APPLICATIONS
================================================================================

This folder contains standalone executable applications for managing your
pickleball ladder league. No Python installation required!

================================================================================
AVAILABLE APPLICATIONS
================================================================================

1. Ladder_League_Manager.exe
   - Standard round robin ladder league
   - All players compete together on all courts
   - Rankings based on performance
   - Player numbers for easy identification

2. Seeded_Ladder_League_Manager.exe
   - Advanced tiered ladder league system
   - First session: Seeding rounds (all players mixed)
   - After seeding: Players split into Tier 1 (top) and Tier 2
   - Tier 1 plays on Courts 2 & 3
   - Tier 2 plays on Courts 1 & 4
   - Automatic promotion/relegation after each session
   - Player numbers for easy identification

3. ROC_City_Ladder_League.exe
   - Original ladder league application

4. ROC_City_Mixed_Doubles.exe
   - Mixed doubles tournament application

================================================================================
HOW TO USE
================================================================================

1. STARTING THE APPLICATION:
   - Simply double-click the .exe file you want to use
   - No installation needed
   - The application will open in a new window

2. FIRST TIME SETUP:
   - Add players using the "Players" tab
   - Or click "Load Demo Players" for testing
   - Each player gets an automatic number assignment (#1, #2, #3, etc.)

3. RUNNING A SESSION:
   - Go to "Rounds" tab
   - Click "Generate Next Round"
   - Player numbers appear with names for easy identification
   - Enter scores in the "Enter Scores" tab
   - View rankings in the "Rankings" tab

4. PLAYER NUMBERS:
   - Each player gets a unique number when added
   - Numbers appear in ALL tabs: Players, Rounds, Scores, Rankings
   - Format: #1 Player Name, #2 Player Name, etc.
   - Makes it easy for organizers to call out assignments

5. DATA STORAGE:
   - Data automatically saves to JSON files in the same folder
   - Ladder_League_Manager.exe → ladder_data.json
   - Seeded_Ladder_League_Manager.exe → seeded_ladder_data.json
   - Your data persists between sessions

================================================================================
SEEDED LADDER LEAGUE WORKFLOW
================================================================================

SESSION 1 (SEEDING):
1. Add all players
2. Generate rounds - all players play mixed on all courts
3. Enter scores for multiple rounds
4. Go to "Session" tab → "End Current Session & Start New"
5. System automatically assigns players to Tier 1 or Tier 2

SESSION 2+ (TIERED PLAY):
1. Generate rounds - players now separated by tier
   - Tier 1 (top players) → Courts 2 & 3
   - Tier 2 (everyone else) → Courts 1 & 4
2. Enter scores
3. End session → automatic promotion/relegation
   - Top 2 from Tier 2 promoted to Tier 1
   - Bottom 2 from Tier 1 relegated to Tier 2

================================================================================
FEATURES
================================================================================

✓ Player number assignments for easy identification
✓ Automatic court assignment based on player count
✓ Smart sit-out rotation (players don't sit consecutive rounds)
✓ Comprehensive statistics tracking
✓ Session history
✓ Export/Import league data
✓ Rankings with point differential
✓ Color-coded positive/negative differentials

================================================================================
SYSTEM REQUIREMENTS
================================================================================

- Windows 10 or later
- No Python installation required
- Approximately 35 MB disk space per executable

================================================================================
TROUBLESHOOTING
================================================================================

Q: The .exe won't open
A: Windows may show a security warning for unsigned applications.
   Click "More info" → "Run anyway"

Q: Where is my data saved?
A: In the same folder as the .exe file, as a .json file

Q: Can I move the .exe to another folder?
A: Yes! The .exe is completely portable. Just move it anywhere you want.

Q: How do I backup my data?
A: Copy the .json file (e.g., ladder_data.json) to a safe location

Q: Player numbers are showing as "?"
A: This happens with old data files. Remove and re-add affected players.

================================================================================
SUPPORT
================================================================================

For questions or issues, contact your league administrator.

Version: December 2025
Built with PyQt6 and PyInstaller
