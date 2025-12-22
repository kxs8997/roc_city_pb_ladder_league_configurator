# ROC City Pickleball - Round Robin League Manager

A comprehensive Windows desktop application for managing round-robin pickleball leagues with intelligent sit-out rotation, game minimums, and point-based rankings.

## Features

### Smart Round-Robin Scheduling
- **Dynamic Court Allocation**: Automatically uses 3 courts for 12-15 players, 4 courts for 16+ players
- **Sit-Out Rotation**: Ensures no player sits out more than 1 round consecutively
- **Game Minimums**: Guarantees every player gets minimum 5 games in an 8-9 round session
- **Fair Distribution**: Players with more games sit out before those with fewer games

### Point Tracking & Rankings
- **Automatic Score Recording**: Enter scores for each completed game
- **Fair Ranking System**: Rankings based on points scored in minimum games only
- **Tie Breaker**: Point differential used when players have equal points
- **Session Management**: Track multiple sessions with persistent player rosters

### Session Planning Examples

**16 Players (4 courts):**
- All 16 play every round
- 8-9 rounds = everyone plays 8-9 games
- Rankings based on all games

**20 Players (4 courts):**
- 16 play, 4 sit each round
- Sit-outs rotate so no one sits twice in a row
- 8 rounds = everyone plays 6-7 games
- Rankings based on first 6 games

**24 Players (4 courts):**
- 16 play, 8 sit each round
- 9 rounds = everyone plays 5-6 games
- Rankings based on first 5 games

**28 Players (4 courts):**
- 16 play, 12 sit each round
- 9 rounds = 24 players get 5 games, 4 players get 6 games
- Rankings based on first 5 games only

## How to Use

### Setup (One-Time)
1. Launch the application
2. Go to **Players** tab
3. Add all league participants (or use "Load Demo Players" for testing)

### Running a Session

#### 1. Generate Rounds
- Go to **Rounds** tab
- Click "Generate Next Round" for each round (typically 8-9 rounds)
- View court assignments and who's sitting out
- Print or display for players

#### 2. Enter Scores
- As games complete, go to **Enter Scores** tab
- Click "Enter Score" for each completed game
- Enter Team 1 and Team 2 scores
- System automatically tracks points and games played

#### 3. View Rankings
- Go to **Rankings** tab
- Click "Refresh Rankings"
- See current standings with:
  - Games played
  - Counted games (minimum across all players)
  - Total points (from counted games only)
  - Point differential

#### 4. Start New Session
- Go to **Session** tab
- Click "Start New Session" when ready for next week
- Clears rounds and scores but keeps player roster
- Players carry over to next session

## Understanding the Algorithm

### Sit-Out Selection
The system prioritizes sitting players who:
1. Didn't sit out in the previous round (hard requirement)
2. Have played more games than others
3. Haven't sat out recently

### Game Counting for Rankings
To ensure fairness when players have different game counts:
- System finds minimum games played across all players
- Rankings count only the first N games for each player (where N = minimum)
- Example: If some played 5 games and others played 6, only first 5 count for everyone
- The 6th game still matters for the players involved, just not for final rankings

### Court Allocation
- **12-15 players**: Uses 3 courts (12 players per round)
- **16-28 players**: Uses 4 courts (16 players per round)
- Ensures you're not running empty courts

## Data Storage

All data saves automatically to `round_robin_data.json`:
- Player roster
- All rounds and court assignments
- Game scores
- Player statistics
- Session number

**Backup Tip**: Copy this file before starting a new session to preserve historical data.

## Typical Session Flow

### Pre-Session (5 minutes)
1. Verify all players are in the system
2. Generate all 8-9 rounds at once
3. Print or display round assignments

### During Session (2 hours)
1. Players check assignments for each round
2. Play games (typically 10-15 minutes per game)
3. Enter scores as games complete
4. Monitor rankings in real-time

### Post-Session (2 minutes)
1. Verify all scores entered
2. Review final rankings
3. Save/export rankings for records
4. Start new session when ready for next week

## Demo Mode

Two demo options available:
- **16 Players**: Perfect for testing full-court scenarios
- **24 Players**: Test sit-out rotation with 8 sitting each round

Use demo mode to:
- Learn the interface
- Test the sit-out rotation
- Verify game minimum enforcement
- Practice score entry

## System Requirements

- Windows 7 or later
- No other software required (if using .exe)

## Troubleshooting

**"Need at least X players"**
- Add more players to meet minimum for court count
- 12 minimum for 3 courts, 16 minimum for 4 courts

**Player sitting out too much**
- Check that you're generating enough rounds
- With 28 players, need 9 rounds to ensure 5 games minimum

**Rankings seem wrong**
- Verify all scores are entered
- Remember: only minimum games count for rankings
- Check that point differential is being used for ties

**Want to undo a score**
- Currently no undo feature
- Start new session if major error
- Or manually track corrections

## Tips for League Organizers

1. **Generate all rounds at start**: Prevents confusion during play
2. **Assign score keepers**: Designate someone to enter scores promptly
3. **Display rankings**: Project rankings tab on screen for real-time updates
4. **Print round sheets**: Physical backup of court assignments
5. **Backup data**: Copy JSON file weekly for historical records

## Future Enhancements

Potential features for future versions:
- Export rankings to PDF/Excel
- Historical session tracking
- Player skill ratings
- Court preference tracking
- Email/SMS notifications for assignments
- Undo score entry
- Manual round editing

## Support

For issues or questions, contact the developer who set this up for your club.
