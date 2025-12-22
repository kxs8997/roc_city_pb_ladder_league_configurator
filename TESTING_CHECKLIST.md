# Testing Checklist for ROC City Ladder League Configurator

## Pre-Testing Setup

### Install Python (if not already installed)
1. Download Python 3.10+ from https://www.python.org/downloads/
2. **CRITICAL**: Check "Add Python to PATH" during installation
3. Restart your terminal/command prompt after installation
4. Verify: Run `python --version` or `py --version`

### Install Dependencies
```bash
cd "C:\Users\karth\OneDrive\Documents\ROC_city_ladder_league_configurator"
python -m pip install -r requirements.txt
```

## Manual Testing Steps

### Test 1: Launch Application
```bash
python ladder_league.py
```
**Expected**: Application window opens with ROC City logo

### Test 2: Add Players
1. Go to "Players" tab
2. Add these test players:
   - Alice
   - Bob
   - Charlie
   - David
   - Emma
   - Frank
   - Grace
   - Henry
   - Iris
   - Jack
   - Kelly
   - Larry
   - Mike
   - Nancy
   - Oscar
   - Paula

**Expected**: All 16 players appear in the list

### Test 3: Generate First Round
1. Go to "Schedule Round" tab
2. Click "Generate New Round"

**Expected**: 
- 4 courts displayed
- Each court has 4 players
- Teams are formed (2v2)
- No errors

### Test 4: Generate Multiple Rounds
1. Click "Generate New Round" 5 more times
2. Note which courts players are assigned to

**Expected**:
- Players rotate through different courts
- No player stuck on same court every time

### Test 5: Check Statistics
1. Go to "Statistics" tab
2. Click "Refresh Statistics"

**Expected**:
- Each player shows court distribution
- Matchup frequency displayed
- Numbers make sense (no player with 0 rounds if all played)

### Test 6: Remove Player
1. Go to "Players" tab
2. Select a player
3. Click "Remove Selected Player"
4. Try to generate a round

**Expected**:
- Player removed from list
- Warning appears (need at least 8 players if <8 remain)

### Test 7: Reset History
1. Go to "Players" tab
2. Click "Reset Match History"
3. Check Statistics tab

**Expected**:
- All court counts reset to 0
- All matchup counts reset to 0
- Player list unchanged

### Test 8: Data Persistence
1. Close the application
2. Check for `ladder_league_data.json` file
3. Reopen application

**Expected**:
- JSON file exists
- All players restored
- All history restored

### Test 9: Edge Cases

**Test 9a: Exactly 8 Players**
- Remove players until only 8 remain
- Generate round
- Expected: 2 courts filled, warning about needing more players

**Test 9b: Odd Number of Players**
- Add 13 players total
- Generate round
- Expected: 3 courts filled (12 players), 1 sitting out

**Test 9c: Duplicate Names**
- Try adding same player name twice
- Expected: Warning message, not added

**Test 9d: Empty Name**
- Try adding empty/whitespace name
- Expected: Warning message, not added

## Build Executable Test

### Build Process
```bash
build_exe.bat
```

**Expected**:
- Build completes without errors
- `dist` folder created
- `ROC_City_Ladder_League.exe` exists in dist folder

### Test Executable
1. Copy `dist\ROC_City_Ladder_League.exe` to a new folder
2. Copy `RocCityPickleball_4k.png` to same folder
3. Double-click the .exe

**Expected**:
- Application launches without Python installed
- All features work identically to Python version
- Logo displays correctly

## Known Limitations to Document

1. **Minimum Players**: Requires 8 players minimum (2 per court × 4 courts)
2. **Optimal Players**: Works best with 16+ players for full rotation
3. **Court Assignment**: Algorithm is probabilistic - won't be perfectly even but trends toward fairness over time
4. **Team Formation**: Teams are randomly paired within each court (not skill-based)

## Bug Report Template

If issues found:
```
**Issue**: [Brief description]
**Steps to Reproduce**: 
1. 
2. 
3. 
**Expected Behavior**: 
**Actual Behavior**: 
**Error Message** (if any): 
```

## Performance Benchmarks

- **Startup Time**: Should be < 3 seconds
- **Round Generation**: Should be < 1 second for 16 players
- **UI Responsiveness**: No freezing during operations
