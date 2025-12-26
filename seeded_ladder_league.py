import sys
import json
import random
import os
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, 
                             QLineEdit, QSpinBox, QTabWidget, QTextEdit,
                             QMessageBox, QGroupBox, QScrollArea, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDialog, QDialogButtonBox,
                             QFormLayout, QFileDialog, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont, QColor


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class SeededLadderLeague:
    def __init__(self):
        self.players = []
        self.session_rounds = []
        self.current_session = 1
        self.player_stats = {}
        self.session_history = []
        self.player_tiers = {}  # Map player name to tier (1-4, where 1 is highest)
        self.is_seeding_session = True # First session is seeding by default
        self.player_numbers = {}  # Map player name to assigned number
        self.next_player_number = 1  # Track next available number
        # Configurable tier-to-court assignments (default: one court per tier for 4-tier system)
        self.tier_court_assignments = {
            1: [4],  # Tier 1 (best) gets Court 4
            2: [3],  # Tier 2 gets Court 3
            3: [2],  # Tier 3 gets Court 2
            4: [1]   # Tier 4 gets Court 1
        }
        
    def add_player(self, name):
        if name and name not in self.players:
            self.players.append(name)
            self.player_stats[name] = {
                'games_played': 0,
                'total_points': 0,
                'total_points_against': 0,
                'rounds_sat_out': 0,
                'last_sat_out_round': -2,
                'game_scores': []
            }
            # Default to Tier 4 (lowest) until seeded/promoted
            self.player_tiers[name] = 4
            # Assign player number
            self.player_numbers[name] = self.next_player_number
            self.next_player_number += 1
            return True
        return False
    
    def remove_player(self, name):
        if name in self.players:
            self.players.remove(name)
            if name in self.player_stats:
                del self.player_stats[name]
            if name in self.player_tiers:
                del self.player_tiers[name]
            if name in self.player_numbers:
                del self.player_numbers[name]
            return True
        return False
        
    def get_tier_players(self, tier):
        """Get list of players in a specific tier"""
        return [p for p in self.players if self.player_tiers.get(p, 2) == tier]

    def get_active_courts(self):
        """Determine number of courts based on player count"""
        player_count = len(self.players)
        
        if player_count >= 16:
            return 4
        elif player_count >= 12:
            return 3
        elif player_count >= 8:
            return 2
        else:
            return 1

    def get_games_played(self, player):
        """Helper to safely get games played count"""
        return self.player_stats.get(player, {}).get('games_played', 0)

    def can_sit_out(self, player, current_round_num):
        """Check if player can sit out this round (didn't sit out last round)"""
        last_sat = self.player_stats[player]['last_sat_out_round']
        return (current_round_num - last_sat) > 1
    
    def select_sitting_players(self, players_pool, num_needed, current_round_num):
        """Select players to sit out from a specific pool of players"""
        num_available = len(players_pool)
        num_sitting = num_available - num_needed
        
        if num_sitting <= 0:
            return []
        
        # Score each player for sitting priority
        sit_scores = []
        for player in players_pool:
            if not self.can_sit_out(player, current_round_num):
                continue
            
            games_played = self.get_games_played(player)
            rounds_sat = self.player_stats[player]['rounds_sat_out']
            last_sat = self.player_stats[player]['last_sat_out_round']
            
            # Higher score = more likely to sit
            # Prioritize balancing games played, then rotation
            score = games_played * 10 - rounds_sat * 20 + (current_round_num - last_sat)
            sit_scores.append((player, score))
        
        # Sort by score (highest first) and select top num_sitting
        sit_scores.sort(key=lambda x: x[1], reverse=True)
        sitting_players = [p for p, _ in sit_scores[:num_sitting]]
        
        # If we don't have enough eligible players (e.g. everyone sat recently), force some to sit
        if len(sitting_players) < num_sitting:
            remaining = [p for p in players_pool if p not in sitting_players]
            # Prioritize those with most games played among remaining
            remaining.sort(key=lambda p: self.get_games_played(p), reverse=True)
            sitting_players.extend(remaining[:num_sitting - len(sitting_players)])
        
        return sitting_players

    def generate_round(self):
        """Generate a new round based on session type (Seeding or Tiered)"""
        current_round_num = len(self.session_rounds) + 1
        
        if self.is_seeding_session:
            return self._generate_seeding_round(current_round_num)
        else:
            return self._generate_tiered_round(current_round_num)

    def _generate_seeding_round(self, current_round_num):
        """Generate round for seeding (mixed play like Round Robin)"""
        num_courts = self.get_active_courts()
        players_needed = num_courts * 4
        
        if len(self.players) < players_needed:
             return None, f"Need at least {players_needed} players for {num_courts} courts"
             
        sitting_players = self.select_sitting_players(self.players, players_needed, current_round_num)
        playing_players = [p for p in self.players if p not in sitting_players]
        random.shuffle(playing_players)
        
        courts = []
        # Assign to courts 1, 2, 3, 4 sequentially
        for court_num in range(1, num_courts + 1):
            start_idx = (court_num - 1) * 4
            court_players = playing_players[start_idx:start_idx + 4]
            
            if len(court_players) == 4:
                courts.append(self._create_court_data(court_num, court_players))
                
        return self._finalize_round(current_round_num, courts, sitting_players)

    def _generate_tiered_round(self, current_round_num):
        """Generate round with configurable tier-to-court assignments"""
        total_courts = self.get_active_courts()
        courts = []
        all_sitting = []
        
        # Process each tier based on configured court assignments
        for tier_num in [1, 2, 3, 4]:
            tier_players = self.get_tier_players(tier_num)
            
            if len(tier_players) < 4:
                # Not enough players for this tier, everyone sits
                all_sitting.extend(tier_players)
                continue
            
            # Get assigned courts for this tier
            assigned_courts = self.tier_court_assignments.get(tier_num, [])
            # Filter to only active courts
            active_assigned_courts = [c for c in assigned_courts if c <= total_courts]
            
            if not active_assigned_courts:
                # No active courts for this tier, everyone sits
                all_sitting.extend(tier_players)
                continue
            
            # Determine how many courts we can actually fill with available players
            max_courts_possible = len(tier_players) // 4
            courts_to_use = min(len(active_assigned_courts), max_courts_possible)
            
            if courts_to_use == 0:
                # Not enough players to fill even one court, everyone sits
                all_sitting.extend(tier_players)
                continue
            
            # Use only the courts we can fill
            courts_for_tier = active_assigned_courts[:courts_to_use]
            players_needed = courts_to_use * 4
            
            # Determine sitting and playing players for this tier
            sitting = self.select_sitting_players(tier_players, players_needed, current_round_num)
            playing = [p for p in tier_players if p not in sitting]
            
            # Shuffle playing players
            random.shuffle(playing)
            
            # Assign players to courts
            for i, court_num in enumerate(courts_for_tier):
                start_idx = i * 4
                court_players = playing[start_idx:start_idx + 4]
                
                if len(court_players) == 4:
                    courts.append(self._create_court_data(court_num, court_players))
                else:
                    # Not enough players for this court, they sit
                    all_sitting.extend(court_players)
            
            # Track sitting players
            all_sitting.extend(sitting)
            # If we have more playing than needed, extras sit
            if len(playing) > players_needed:
                all_sitting.extend(playing[players_needed:])
        
        return self._finalize_round(current_round_num, courts, all_sitting)

    def _create_court_data(self, court_num, players):
        return {
            'court': court_num,
            'players': players,
            'team1': players[:2],
            'team2': players[2:],
            'team1_score': 0,
            'team2_score': 0,
            'completed': False
        }

    def _finalize_round(self, current_round_num, courts, sitting_players):
        # Update sit-out tracking
        for player in sitting_players:
            self.player_stats[player]['rounds_sat_out'] += 1
            self.player_stats[player]['last_sat_out_round'] = current_round_num
        
        round_data = {
            'round_number': current_round_num,
            'courts': courts,
            'sitting_players': sitting_players
        }
        
        self.session_rounds.append(round_data)
        return round_data, None

    def record_game_score(self, round_num, court_num, team1_score, team2_score, team1=None, team2=None):
        """Record scores for a completed game"""
        if round_num < 1 or round_num > len(self.session_rounds):
            return False
        
        round_data = self.session_rounds[round_num - 1]
        court = None
        
        # Find the specific court/match
        for c in round_data['courts']:
            if c['court'] == court_num:
                # If teams are provided, match them (for cases with multiple matches on same court)
                if team1 and team2:
                    if set(c['team1']) == set(team1) and set(c['team2']) == set(team2):
                        court = c
                        break
                # Fallback: if not completed, assume this is the one (or first one found)
                elif not c.get('completed', False):
                    court = c
                    break
        
        # If we still haven't found it, try finding ANY match on this court that matches teams
        if not court and team1 and team2:
             for c in round_data['courts']:
                if c['court'] == court_num:
                    if set(c['team1']) == set(team1) and set(c['team2']) == set(team2):
                        court = c
                        break
        
        if not court:
            return False
        
        court['team1_score'] = team1_score
        court['team2_score'] = team2_score
        court['completed'] = True
        
        # Update player stats
        self._update_stats_for_team(court['team1'], team1_score, team2_score, round_num)
        self._update_stats_for_team(court['team2'], team2_score, team1_score, round_num)
        
        return True
        
    def _update_stats_for_team(self, team, points_for, points_against, round_num):
        for player in team:
            self.player_stats[player]['games_played'] += 1
            self.player_stats[player]['total_points'] += points_for
            self.player_stats[player]['total_points_against'] += points_against
    def get_rankings(self):
        """Get player rankings based on points"""
        if not self.players:
            return []
        
        rankings = []
        for player in self.players:
            stats = self.player_stats[player]
            games_played = stats['games_played']
            points = stats['total_points']
            points_against = stats['total_points_against']
            differential = points - points_against
            
            rankings.append({
                'player': player,
                'games_played': games_played,
                'counted_games': games_played,
                'points': points,
                'points_against': points_against,
                'differential': differential,
                'tier': self.player_tiers.get(player, 4)
            })
        
        # Sort by tier (asc), then points (desc), then differential (desc)
        # This ensures Tier 1 players are always ranked highest, even after a new session starts
        rankings.sort(key=lambda x: (x['tier'], -x['points'], -x['differential']))
        
        return rankings

    def perform_seeding(self):
        """Assign 4 tiers based on current rankings (used after first session)"""
        rankings = self.get_rankings()
        total_players = len(rankings)
        
        # Divide players into 4 tiers as evenly as possible
        # Each tier should have 4-8 players ideally for rotation
        players_per_tier = max(4, total_players // 4)
        
        tier1_count = min(players_per_tier, total_players)
        tier2_count = min(players_per_tier, max(0, total_players - tier1_count))
        tier3_count = min(players_per_tier, max(0, total_players - tier1_count - tier2_count))
        tier4_count = total_players - tier1_count - tier2_count - tier3_count
        
        # Assign tiers based on rankings
        idx = 0
        tier_assignments = {}
        
        # Tier 1 (best players)
        for i in range(tier1_count):
            tier_assignments[rankings[idx]['player']] = 1
            idx += 1
        
        # Tier 2
        for i in range(tier2_count):
            tier_assignments[rankings[idx]['player']] = 2
            idx += 1
        
        # Tier 3
        for i in range(tier3_count):
            tier_assignments[rankings[idx]['player']] = 3
            idx += 1
        
        # Tier 4 (remaining players)
        for i in range(tier4_count):
            tier_assignments[rankings[idx]['player']] = 4
            idx += 1
        
        # Apply tier assignments
        for player, tier in tier_assignments.items():
            self.player_tiers[player] = tier
            
        self.is_seeding_session = False
        
        # Return tier lists for display
        tier1_players = [p for p, t in tier_assignments.items() if t == 1]
        tier2_players = [p for p, t in tier_assignments.items() if t == 2]
        tier3_players = [p for p, t in tier_assignments.items() if t == 3]
        tier4_players = [p for p, t in tier_assignments.items() if t == 4]
        
        return tier1_players, tier2_players, tier3_players, tier4_players

    def perform_promotion_relegation(self):
        """Move players between tiers based on performance (4-tier system)"""
        # Get rankings for each tier separately
        tier1_rankings = [r for r in self.get_rankings() if r['tier'] == 1]
        tier2_rankings = [r for r in self.get_rankings() if r['tier'] == 2]
        tier3_rankings = [r for r in self.get_rankings() if r['tier'] == 3]
        tier4_rankings = [r for r in self.get_rankings() if r['tier'] == 4]
        
        promoted = []
        relegated = []
        
        num_swap = 2  # Number of players to swap between adjacent tiers
        
        # Tier 1 <-> Tier 2
        if len(tier1_rankings) >= 4 and len(tier2_rankings) >= 4:
            # Relegate bottom 2 from Tier 1 to Tier 2
            for r in tier1_rankings[-num_swap:]:
                self.player_tiers[r['player']] = 2
                relegated.append((r['player'], 1, 2))
            
            # Promote top 2 from Tier 2 to Tier 1
            for r in tier2_rankings[:num_swap]:
                self.player_tiers[r['player']] = 1
                promoted.append((r['player'], 2, 1))
        
        # Tier 2 <-> Tier 3
        if len(tier2_rankings) >= 4 and len(tier3_rankings) >= 4:
            # Relegate bottom 2 from Tier 2 to Tier 3
            for r in tier2_rankings[-num_swap:]:
                self.player_tiers[r['player']] = 3
                relegated.append((r['player'], 2, 3))
            
            # Promote top 2 from Tier 3 to Tier 2
            for r in tier3_rankings[:num_swap]:
                self.player_tiers[r['player']] = 2
                promoted.append((r['player'], 3, 2))
        
        # Tier 3 <-> Tier 4
        if len(tier3_rankings) >= 4 and len(tier4_rankings) >= 4:
            # Relegate bottom 2 from Tier 3 to Tier 4
            for r in tier3_rankings[-num_swap:]:
                self.player_tiers[r['player']] = 4
                relegated.append((r['player'], 3, 4))
            
            # Promote top 2 from Tier 4 to Tier 3
            for r in tier4_rankings[:num_swap]:
                self.player_tiers[r['player']] = 3
                promoted.append((r['player'], 4, 3))
        
        return promoted, relegated

    def new_session(self):
        """Start a new session, saving current session to history and applying seeding/promo/relegation"""
        rankings = self.get_rankings()
        
        # Logic to update tiers BEFORE clearing stats for next session
        promoted = []
        relegated = []
        seeded_tier1 = []
        seeded_tier2 = []
        seeded_tier3 = []
        seeded_tier4 = []
        
        if self.is_seeding_session:
            seeded_tier1, seeded_tier2, seeded_tier3, seeded_tier4 = self.perform_seeding()
        else:
            promoted, relegated = self.perform_promotion_relegation()
        
        # Save current session to history
        if self.session_rounds:
            session_data = {
                'session_number': self.current_session,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'rounds': self.session_rounds,
                'rankings': rankings,
                'player_count': len(self.players),
                'is_seeding': self.is_seeding_session, # This was the state DURING the session
                'promoted': promoted,
                'relegated': relegated,
                'seeded_tier1': seeded_tier1,
                'seeded_tier2': seeded_tier2,
                'seeded_tier3': seeded_tier3,
                'seeded_tier4': seeded_tier4
            }
            self.session_history.append(session_data)
        
        # Clear current session stats
        self.session_rounds = []
        self.current_session += 1
        
        # Reset stats but KEEP TIERS
        for player in self.players:
            self.player_stats[player] = {
                'games_played': 0,
                'total_points': 0,
                'total_points_against': 0,
                'rounds_sat_out': 0,
                'last_sat_out_round': -2,
                'game_scores': []
            }

    def clear_current_session(self):
        self.session_rounds = []
        for player in self.players:
            self.player_stats[player] = {
                'games_played': 0,
                'total_points': 0,
                'total_points_against': 0,
                'rounds_sat_out': 0,
                'last_sat_out_round': -2,
                'game_scores': []
            }
    
    def clear_history(self):
        self.session_history = []
    
    def reset_all(self):
        self.session_rounds = []
        self.current_session = 1
        self.session_history = []
        self.is_seeding_session = True
        self.player_tiers = {}
        for player in self.players:
            self.player_stats[player] = {
                'games_played': 0,
                'total_points': 0,
                'total_points_against': 0,
                'rounds_sat_out': 0,
                'last_sat_out_round': -2,
                'game_scores': []
            }
            self.player_tiers[player] = 2

    def clear_all_data(self):
        self.players = []
        self.session_rounds = []
        self.current_session = 1
        self.player_stats = {}
        self.session_history = []
        self.player_tiers = {}
        self.is_seeding_session = True
        self.player_numbers = {}
        self.next_player_number = 1

    def save_to_file(self, filename):
        data = {
            'players': self.players,
            'session_rounds': self.session_rounds,
            'current_session': self.current_session,
            'player_stats': self.player_stats,
            'session_history': self.session_history,
            'player_tiers': self.player_tiers,
            'is_seeding_session': self.is_seeding_session,
            'player_numbers': self.player_numbers,
            'next_player_number': self.next_player_number,
            'tier_court_assignments': self.tier_court_assignments
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filename):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                self.players = data.get('players', [])
                self.session_rounds = data.get('session_rounds', [])
                self.current_session = data.get('current_session', 1)
                self.player_stats = data.get('player_stats', {})
                self.session_history = data.get('session_history', [])
                self.player_tiers = data.get('player_tiers', {})
                self.is_seeding_session = data.get('is_seeding_session', True)
                self.player_numbers = data.get('player_numbers', {})
                self.next_player_number = data.get('next_player_number', 1)
                # Convert keys to integers for tier_court_assignments
                raw_assignments = data.get('tier_court_assignments', {
                    1: [4],
                    2: [3],
                    3: [2],
                    4: [1]
                })
                loaded_assignments = {}
                for k, v in raw_assignments.items():
                    try:
                        loaded_assignments[int(k)] = v
                    except:
                        loaded_assignments[k] = v
                
                # Migrate old 2-tier assignments to new 4-tier default
                if loaded_assignments.get(1) == [2, 3] and loaded_assignments.get(2) == [1, 4]:
                    # Old default detected, migrate to new 4-tier default
                    self.tier_court_assignments = {
                        1: [4],
                        2: [3],
                        3: [2],
                        4: [1]
                    }
                else:
                    self.tier_court_assignments = loaded_assignments
            return True
        except:
            return False


class BigScreenDisplay(QWidget):
    def __init__(self, league, parent=None):
        super().__init__(parent)
        self.league = league
        self.setWindowTitle('Current Round - Big Screen Display')
        self.setWindowFlags(Qt.WindowType.Window)
        self.setStyleSheet("background-color: #1a1a2e;")
        
        # Get screen geometry with fallback
        try:
            screen = QApplication.primaryScreen()
            if screen:
                geometry = screen.geometry()
                self.screen_width = geometry.width()
                self.screen_height = geometry.height()
            else:
                self.screen_width = 1920
                self.screen_height = 1080
        except:
            self.screen_width = 1920
            self.screen_height = 1080
        
        # Main layout - no scrolling
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # Header with logo and title
        header_layout = QHBoxLayout()
        
        # Logo
        logo_path = resource_path('RocCityPickleball_4k.png')
        if os.path.exists(logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(logo_path)
            logo_height = int(self.screen_height * 0.08)
            scaled_pixmap = pixmap.scaledToHeight(logo_height, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            header_layout.addWidget(logo_label)
        
        # Title container
        title_container = QVBoxLayout()
        
        # Title
        self.title_label = QLabel('CURRENT ROUND')
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(int(self.screen_height * 0.035))
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #00d4ff;")
        title_container.addWidget(self.title_label)
        
        # Round number and mode
        self.round_label = QLabel()
        self.round_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        round_font = QFont()
        round_font.setPointSize(int(self.screen_height * 0.028))
        round_font.setBold(True)
        self.round_label.setFont(round_font)
        self.round_label.setStyleSheet("color: #ffffff;")
        title_container.addWidget(self.round_label)
        
        # Date and time
        self.datetime_label = QLabel()
        self.datetime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        datetime_font = QFont()
        datetime_font.setPointSize(int(self.screen_height * 0.018))
        self.datetime_label.setFont(datetime_font)
        self.datetime_label.setStyleSheet("color: #aaaaaa;")
        title_container.addWidget(self.datetime_label)
        
        # Mode indicator
        self.mode_label = QLabel()
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mode_font = QFont()
        mode_font.setPointSize(int(self.screen_height * 0.015))
        mode_font.setBold(True)
        self.mode_label.setFont(mode_font)
        title_container.addWidget(self.mode_label)
        
        header_layout.addLayout(title_container)
        header_layout.addStretch()
        
        # Buttons in header
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(5)
        
        # Navigation buttons row
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(5)
        
        btn_font_size = int(self.screen_height * 0.015)
        
        # Previous Round button
        prev_round_btn = QPushButton('◀ Prev')
        prev_round_btn.clicked.connect(self.show_previous_round)
        prev_round_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FF9800;
                color: white;
                font-size: {btn_font_size}pt;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #F57C00;
            }}
        """)
        nav_layout.addWidget(prev_round_btn)
        
        # Next Round button
        next_round_btn = QPushButton('Next ▶')
        next_round_btn.clicked.connect(self.show_next_round)
        next_round_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FF9800;
                color: white;
                font-size: {btn_font_size}pt;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #F57C00;
            }}
        """)
        nav_layout.addWidget(next_round_btn)
        
        buttons_layout.addLayout(nav_layout)
        
        # Generate Next Round button
        gen_round_btn = QPushButton('✚ Generate Round')
        gen_round_btn.clicked.connect(self.generate_next_round)
        gen_round_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                font-size: {btn_font_size}pt;
                font-weight: bold;
                padding: 8px 15px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
        """)
        buttons_layout.addWidget(gen_round_btn)
        
        # Refresh button
        refresh_btn = QPushButton('↻ Refresh')
        refresh_btn.clicked.connect(self.update_display)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #00d4ff;
                color: #1a1a2e;
                font-size: {btn_font_size}pt;
                font-weight: bold;
                padding: 8px 15px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #00a8cc;
            }}
        """)
        buttons_layout.addWidget(refresh_btn)
        
        header_layout.addLayout(buttons_layout)
        
        layout.addLayout(header_layout)
        
        # Courts container - takes remaining space
        self.courts_widget = QWidget()
        self.courts_layout = QVBoxLayout(self.courts_widget)
        self.courts_layout.setSpacing(8)
        self.courts_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.courts_widget, 1)
        
        # Sitting players at bottom
        self.sitting_label = QLabel()
        self.sitting_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sitting_label.setWordWrap(True)
        sitting_font = QFont()
        sitting_font.setPointSize(int(self.screen_height * 0.02))
        sitting_font.setBold(True)
        self.sitting_label.setFont(sitting_font)
        self.sitting_label.setStyleSheet("color: #ff6b6b; padding: 10px; background-color: #2d2d44; border-radius: 8px;")
        layout.addWidget(self.sitting_label)
        
        # Track which round is being displayed (None = latest)
        self.displayed_round_index = None
        
        # Show maximized
        self.showMaximized()
        self.update_display()
    
    def show_previous_round(self):
        if not self.league.session_rounds:
            return
        
        if self.displayed_round_index is None:
            # Currently showing latest, go to second-to-last
            if len(self.league.session_rounds) > 1:
                self.displayed_round_index = len(self.league.session_rounds) - 2
        elif self.displayed_round_index > 0:
            self.displayed_round_index -= 1
        
        self.update_display()
    
    def show_next_round(self):
        if not self.league.session_rounds:
            return
        
        if self.displayed_round_index is None:
            # Already showing latest
            return
        
        self.displayed_round_index += 1
        if self.displayed_round_index >= len(self.league.session_rounds) - 1:
            # Back to showing latest
            self.displayed_round_index = None
        
        self.update_display()
    
    def generate_next_round(self):
        # Generate next round in the parent window
        if self.parent():
            self.parent().generate_round()
            self.displayed_round_index = None  # Show the new latest round
            self.update_display()
    
    def update_display(self):
        # Update date and time
        from datetime import datetime
        now = datetime.now()
        self.datetime_label.setText(now.strftime("%A, %B %d, %Y  •  %I:%M %p"))
        
        if not self.league.session_rounds:
            self.round_label.setText("No rounds generated yet")
            self.mode_label.setText("")
            self.clear_courts()
            self.sitting_label.setText("")
            return
        
        # Get the round to display
        if self.displayed_round_index is None:
            current_round = self.league.session_rounds[-1]
            round_indicator = "(Latest)"
        else:
            current_round = self.league.session_rounds[self.displayed_round_index]
            round_indicator = f"({self.displayed_round_index + 1} of {len(self.league.session_rounds)})"
        
        round_num = current_round['round_number']
        self.round_label.setText(f"ROUND {round_num} {round_indicator}")
        
        # Show mode
        if self.league.is_seeding_session:
            self.mode_label.setText("🎯 SEEDING SESSION - All Players Mixed")
            self.mode_label.setStyleSheet("color: #f39c12; padding: 10px;")
        else:
            # Build dynamic tier-to-court display
            tier_assignments = []
            for tier_num in [1, 2, 3, 4]:
                courts = self.league.tier_court_assignments.get(tier_num, [])
                if courts:
                    court_str = ','.join(map(str, courts))
                    tier_assignments.append(f"Tier {tier_num}: Court{'s' if len(courts) > 1 else ''} {court_str}")
            
            mode_text = "🏆 TIERED PLAY - " + " | ".join(tier_assignments)
            self.mode_label.setText(mode_text)
            self.mode_label.setStyleSheet("color: #4ecca3; padding: 10px;")
        
        # Clear existing courts
        self.clear_courts()
        
        # Display each court
        for court_data in current_round['courts']:
            court_widget = self.create_court_widget(court_data)
            self.courts_layout.addWidget(court_widget)
        
        # Display sitting players
        if current_round['sitting_players']:
            sitting_text = "SITTING OUT: " + " • ".join([
                f"#{self.league.player_numbers.get(p, '?')} {p}" 
                for p in current_round['sitting_players']
            ])
            self.sitting_label.setText(sitting_text)
            self.sitting_label.show()
        else:
            self.sitting_label.hide()
    
    def clear_courts(self):
        while self.courts_layout.count():
            item = self.courts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def create_court_widget(self, court_data):
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #2d2d44;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Court number - compact sizing with responsive font
        court_font_size = int(self.screen_height * 0.022)
        court_label = QLabel(f"COURT\n{court_data['court']}")
        court_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        court_font = QFont()
        court_font.setPointSize(court_font_size)
        court_font.setBold(True)
        court_label.setFont(court_font)
        court_label.setStyleSheet("""
            color: #00d4ff;
            background-color: #1a1a2e;
            border-radius: 6px;
            padding: 10px;
            min-width: 90px;
        """)
        layout.addWidget(court_label)
        
        # Teams side by side with VS in middle
        teams_layout = QHBoxLayout()
        teams_layout.setSpacing(10)
        
        # Team 1 - horizontal display
        team1_players = []
        for player in court_data['team1']:
            player_num = self.league.player_numbers.get(player, '?')
            team1_players.append(f"#{player_num} {player}")
        
        team1_label = QLabel(" & ".join(team1_players))
        team1_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        name_font = QFont()
        name_font.setPointSize(int(self.screen_height * 0.02))
        name_font.setBold(True)
        team1_label.setFont(name_font)
        team1_label.setStyleSheet("color: #4ecca3; padding: 5px;")
        teams_layout.addWidget(team1_label, 1)
        
        # VS label
        vs_label = QLabel("VS")
        vs_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vs_font = QFont()
        vs_font.setPointSize(int(self.screen_height * 0.022))
        vs_font.setBold(True)
        vs_label.setFont(vs_font)
        vs_label.setStyleSheet("color: #ff6b6b; padding: 5px 15px;")
        teams_layout.addWidget(vs_label, 0)
        
        # Team 2 - horizontal display
        team2_players = []
        for player in court_data['team2']:
            player_num = self.league.player_numbers.get(player, '?')
            team2_players.append(f"#{player_num} {player}")
        
        team2_label = QLabel(" & ".join(team2_players))
        team2_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        team2_label.setFont(name_font)
        team2_label.setStyleSheet("color: #f39c12; padding: 5px;")
        teams_layout.addWidget(team2_label, 1)
        
        layout.addLayout(teams_layout, 1)
        
        # Score (if completed)
        if court_data.get('completed', False):
            score_label = QLabel(f"{court_data['team1_score']}\n-\n{court_data['team2_score']}")
            score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            score_font = QFont()
            score_font.setPointSize(int(self.screen_height * 0.025))
            score_font.setBold(True)
            score_label.setFont(score_font)
            score_label.setStyleSheet("""
                color: #ffffff;
                background-color: #1a1a2e;
                border-radius: 8px;
                padding: 12px;
                min-width: 80px;
            """)
            layout.addWidget(score_label)
        
        return widget


class ScoreDialog(QDialog):
    def __init__(self, round_num, court_num, team1, team2, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'Enter Scores - Round {round_num}, Court {court_num}')
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        team1_label = QLabel(f"Team 1: {team1[0]} & {team1[1]}")
        team1_label.setStyleSheet("font-weight: bold;")
        form.addRow(team1_label)
        
        self.team1_score = QSpinBox()
        self.team1_score.setRange(0, 99)
        self.team1_score.setValue(11)
        form.addRow("Team 1 Score:", self.team1_score)
        
        form.addRow(QLabel(""))
        
        team2_label = QLabel(f"Team 2: {team2[0]} & {team2[1]}")
        team2_label.setStyleSheet("font-weight: bold;")
        form.addRow(team2_label)
        
        self.team2_score = QSpinBox()
        self.team2_score.setRange(0, 99)
        self.team2_score.setValue(0)
        form.addRow("Team 2 Score:", self.team2_score)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_scores(self):
        return self.team1_score.value(), self.team2_score.value()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.league = SeededLadderLeague()
        self.data_file = Path('seeded_ladder_data.json')
        
        if self.data_file.exists():
            self.league.load_from_file(self.data_file)
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('ROC City Pickleball - Seeded Ladder League')
        self.setGeometry(100, 100, 1100, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        logo_path = resource_path('RocCityPickleball_4k.png')
        if os.path.exists(logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaledToWidth(300, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(logo_label)
        
        title_text = 'Seeded Ladder League Manager'
        if self.league.is_seeding_session:
            title_text += ' (Seeding Session)'
        else:
            title_text += ' (Tiered Play)'
            
        self.title_label = QLabel(title_text)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.title_label)
        
        self.status_label = QLabel('Ready')
        main_layout.addWidget(self.status_label)
        
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        tabs.addTab(self.create_players_tab(), 'Players')
        tabs.addTab(self.create_player_numbers_tab(), 'Player Numbers')
        tabs.addTab(self.create_settings_tab(), 'Settings')
        tabs.addTab(self.create_rounds_tab(), 'Rounds')
        tabs.addTab(self.create_scores_tab(), 'Enter Scores')
        tabs.addTab(self.create_rankings_tab(), 'Rankings')
        tabs.addTab(self.create_history_tab(), 'History')
        tabs.addTab(self.create_session_tab(), 'Session')
    
    def create_players_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        add_group = QGroupBox('Add Player')
        add_layout = QHBoxLayout()
        
        self.player_name_input = QLineEdit()
        self.player_name_input.setPlaceholderText('Enter player name')
        self.player_name_input.returnPressed.connect(self.add_player)
        add_layout.addWidget(self.player_name_input)
        
        add_btn = QPushButton('Add Player')
        add_btn.clicked.connect(self.add_player)
        add_layout.addWidget(add_btn)
        
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)
        
        players_group = QGroupBox('Current Players')
        players_layout = QVBoxLayout()
        
        self.players_list = QListWidget()
        self.update_players_list()
        players_layout.addWidget(self.players_list)
        
        remove_btn = QPushButton('Remove Selected Player')
        remove_btn.clicked.connect(self.remove_player)
        players_layout.addWidget(remove_btn)
        
        players_group.setLayout(players_layout)
        layout.addWidget(players_group)
        
        buttons_layout = QHBoxLayout()
        
        demo_btn_12 = QPushButton('Load Demo Players (12)')
        demo_btn_12.clicked.connect(lambda checked: self.load_demo_players(12))
        demo_btn_12.setStyleSheet('QPushButton { background-color: #4CAF50; color: white; padding: 8px; }')
        buttons_layout.addWidget(demo_btn_12)
        
        demo_btn_16 = QPushButton('Load Demo Players (16)')
        demo_btn_16.clicked.connect(lambda checked: self.load_demo_players(16))
        demo_btn_16.setStyleSheet('QPushButton { background-color: #4CAF50; color: white; padding: 8px; }')
        buttons_layout.addWidget(demo_btn_16)
        
        demo_btn_20 = QPushButton('Load Demo Players (20)')
        demo_btn_20.clicked.connect(lambda checked: self.load_demo_players(20))
        demo_btn_20.setStyleSheet('QPushButton { background-color: #4CAF50; color: white; padding: 8px; }')
        buttons_layout.addWidget(demo_btn_20)
        
        layout.addLayout(buttons_layout)
        
        return widget
    
    def create_player_numbers_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info_label = QLabel('Player Number Assignments')
        info_font = QFont()
        info_font.setPointSize(12)
        info_font.setBold(True)
        info_label.setFont(info_font)
        layout.addWidget(info_label)
        
        description = QLabel('Each player is assigned a unique number for easy identification during play.')
        description.setWordWrap(True)
        layout.addWidget(description)
        
        self.player_numbers_table = QTableWidget()
        self.player_numbers_table.setColumnCount(3)
        self.player_numbers_table.setHorizontalHeaderLabels(['Number', 'Player Name', 'Tier'])
        self.player_numbers_table.horizontalHeader().setStretchLastSection(True)
        self.player_numbers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.player_numbers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.player_numbers_table)
        
        self.update_player_numbers_table()
        
        return widget
    
    def create_settings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info_label = QLabel('Tier-to-Court Assignments')
        info_font = QFont()
        info_font.setPointSize(12)
        info_font.setBold(True)
        info_label.setFont(info_font)
        layout.addWidget(info_label)
        
        description = QLabel('Configure which courts each tier plays on. Default: Tier 1→Court 4, Tier 2→Court 3, Tier 3→Court 2, Tier 4→Court 1.')
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Create input fields for each tier
        self.tier_court_inputs = {}
        
        for tier_num in [1, 2, 3, 4]:
            tier_group = QGroupBox(f'Tier {tier_num}')
            tier_layout = QHBoxLayout()
            
            label = QLabel('Courts (comma-separated):')
            tier_layout.addWidget(label)
            
            court_input = QLineEdit()
            current_courts = self.league.tier_court_assignments.get(tier_num, [])
            court_input.setText(','.join(map(str, current_courts)))
            court_input.setPlaceholderText('e.g., 1,2 or 3')
            self.tier_court_inputs[tier_num] = court_input
            tier_layout.addWidget(court_input)
            
            tier_group.setLayout(tier_layout)
            layout.addWidget(tier_group)
        
        # Save button
        save_btn = QPushButton('Save Court Assignments')
        save_btn.clicked.connect(self.save_court_assignments)
        save_btn.setStyleSheet('QPushButton { font-size: 12pt; padding: 10px; background-color: #4CAF50; color: white; }')
        layout.addWidget(save_btn)
        
        # Reset to default button
        reset_btn = QPushButton('Reset to Default')
        reset_btn.clicked.connect(self.reset_court_assignments)
        reset_btn.setStyleSheet('QPushButton { font-size: 12pt; padding: 10px; background-color: #FF9800; color: white; }')
        layout.addWidget(reset_btn)
        
        layout.addStretch()
        
        return widget
    
    def create_rounds_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        mode_text = "Seeding Mode: Everyone plays everyone (Random)" if self.league.is_seeding_session else "Tiered Mode: Top Tier on Courts 2&3, Lower Tier on Courts 1&4"
        info_label = QLabel(f'{mode_text}\nGenerate rounds for your session.')
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-weight: bold;")
        self.rounds_info_label = info_label
        layout.addWidget(info_label)
        
        gen_layout = QHBoxLayout()
        generate_btn = QPushButton('Generate Next Round')
        generate_btn.clicked.connect(self.generate_round)
        generate_btn.setStyleSheet('QPushButton { font-size: 14pt; padding: 10px; background-color: #88cc00; }')
        gen_layout.addWidget(generate_btn)
        
        big_screen_btn = QPushButton('📺 Big Screen Display')
        big_screen_btn.clicked.connect(self.open_big_screen)
        big_screen_btn.setStyleSheet('QPushButton { font-size: 14pt; padding: 10px; background-color: #2196F3; color: white; }')
        gen_layout.addWidget(big_screen_btn)
        
        sim_btn = QPushButton('🎲 Sim Scores')
        sim_btn.clicked.connect(self.simulate_scores)
        sim_btn.setStyleSheet('QPushButton { font-size: 14pt; padding: 10px; background-color: #9C27B0; color: white; }')
        gen_layout.addWidget(sim_btn)
        
        self.round_count_label = QLabel('Rounds: 0')
        self.round_count_label.setStyleSheet('font-size: 14pt; font-weight: bold;')
        gen_layout.addWidget(self.round_count_label)
        
        layout.addLayout(gen_layout)
        
        self.rounds_display = QTextEdit()
        self.rounds_display.setReadOnly(True)
        self.rounds_display.setStyleSheet('QTextEdit { font-family: Courier; font-size: 10pt; }')
        layout.addWidget(self.rounds_display)
        
        return widget
    
    def create_scores_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Left side: Scores table
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        info_label = QLabel('Enter scores for completed games')
        left_layout.addWidget(info_label)
        
        self.scores_table = QTableWidget()
        self.scores_table.setColumnCount(6)
        self.scores_table.setHorizontalHeaderLabels(['Round', 'Court', 'Team 1', 'Team 2', 'Score', 'Action'])
        self.scores_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        left_layout.addWidget(self.scores_table)
        
        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self.update_scores_table)
        left_layout.addWidget(refresh_btn)
        
        layout.addWidget(left_widget, 3)
        
        # Right side: Player numbers reference
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        ref_label = QLabel('Player Numbers Reference')
        ref_font = QFont()
        ref_font.setPointSize(11)
        ref_font.setBold(True)
        ref_label.setFont(ref_font)
        right_layout.addWidget(ref_label)
        
        self.scores_player_numbers_table = QTableWidget()
        self.scores_player_numbers_table.setColumnCount(3)
        self.scores_player_numbers_table.setHorizontalHeaderLabels(['#', 'Player', 'Tier'])
        self.scores_player_numbers_table.horizontalHeader().setStretchLastSection(True)
        self.scores_player_numbers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.scores_player_numbers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.scores_player_numbers_table.verticalHeader().setVisible(False)
        right_layout.addWidget(self.scores_player_numbers_table)
        
        self.update_scores_player_numbers()
        
        layout.addWidget(right_widget, 1)
        
        return widget
    
    def create_rankings_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Left side: Current session rankings
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        current_label = QLabel('Current Session Rankings')
        current_label.setStyleSheet('font-size: 12pt; font-weight: bold;')
        left_layout.addWidget(current_label)
        
        info_label = QLabel('Points from this session. Tiers updated at end of session.')
        left_layout.addWidget(info_label)
        
        self.rankings_table = QTableWidget()
        self.rankings_table.setColumnCount(6)
        self.rankings_table.setHorizontalHeaderLabels(['Rank', 'Tier', 'Player', 'Games', 'Points', 'Diff'])
        left_layout.addWidget(self.rankings_table)
        
        refresh_btn = QPushButton('Refresh Rankings')
        refresh_btn.clicked.connect(self.update_rankings)
        left_layout.addWidget(refresh_btn)
        
        layout.addWidget(left_widget, 2)
        
        # Right side: Last session rankings
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        last_label = QLabel('Last Session Final Standings')
        last_label.setStyleSheet('font-size: 12pt; font-weight: bold;')
        right_layout.addWidget(last_label)
        
        self.last_session_table = QTableWidget()
        self.last_session_table.setColumnCount(5)
        self.last_session_table.setHorizontalHeaderLabels(['Rank', 'Tier', 'Player', 'Points', 'Diff'])
        right_layout.addWidget(self.last_session_table)
        
        layout.addWidget(right_widget, 1)
        
        return widget
    
    def create_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info_label = QLabel('Session History - View Past Results')
        info_label.setStyleSheet('font-size: 14pt; font-weight: bold;')
        layout.addWidget(info_label)
        
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.show_history_details)
        layout.addWidget(self.history_list)
        
        self.history_details = QTextEdit()
        self.history_details.setReadOnly(True)
        layout.addWidget(self.history_details)
        
        buttons_layout = QHBoxLayout()
        refresh_history_btn = QPushButton('Refresh')
        refresh_history_btn.clicked.connect(self.update_history_list)
        buttons_layout.addWidget(refresh_history_btn)
        layout.addLayout(buttons_layout)
        
        self.update_history_list()
        
        return widget
    
    def create_session_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info_label = QLabel('Session Management')
        info_label.setStyleSheet('font-size: 14pt; font-weight: bold;')
        layout.addWidget(info_label)
        
        self.session_info = QTextEdit()
        self.session_info.setReadOnly(True)
        self.session_info.setMaximumHeight(200)
        layout.addWidget(self.session_info)
        
        new_session_btn = QPushButton('End Current Session & Start New')
        new_session_btn.clicked.connect(self.new_session)
        new_session_btn.setStyleSheet('QPushButton { background-color: #ff9800; color: white; padding: 10px; font-size: 12pt; }')
        layout.addWidget(new_session_btn)
        
        data_group = QGroupBox('Data Management')
        data_layout = QVBoxLayout()
        
        reset_all_btn = QPushButton('Reset All Data (Keep Players)')
        reset_all_btn.clicked.connect(self.reset_all_data)
        reset_all_btn.setStyleSheet('QPushButton { background-color: #E91E63; color: white; padding: 6px; }')
        data_layout.addWidget(reset_all_btn)
        
        clear_all_btn = QPushButton('⚠️ Clear ALL Data (Delete Everything)')
        clear_all_btn.clicked.connect(self.clear_all_data)
        clear_all_btn.setStyleSheet('QPushButton { background-color: #D32F2F; color: white; padding: 6px; font-weight: bold; }')
        data_layout.addWidget(clear_all_btn)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        self.update_session_info()
        
        return widget
    
    def add_player(self):
        name = self.player_name_input.text().strip()
        if self.league.add_player(name):
            self.player_name_input.clear()
            self.update_players_list()
            self.update_player_numbers_table()
            self.update_scores_player_numbers()
            self.save_data()
            self.status_label.setText(f'Added player: {name}')
        else:
            QMessageBox.warning(self, 'Error', 'Player name is empty or already exists')
    
    def remove_player(self):
        current_item = self.players_list.currentItem()
        if current_item:
            display_text = current_item.text()
            # Extract player name from "#X - Name (Tier)" format
            if ' - ' in display_text:
                name = display_text.split(' - ', 1)[1].split(' (')[0]
            else:
                name = display_text.split(' (')[0]
            if self.league.remove_player(name):
                self.update_players_list()
                self.update_player_numbers_table()
                self.update_scores_player_numbers()
                self.save_data()
                self.status_label.setText(f'Removed player: {name}')
    
    def load_demo_players(self, count=16):
        """Load demo players with tier assignments based on count"""
        reply = QMessageBox.question(self, 'Load Demo Players',
                                     f'Load {count} demo players? This will clear existing data.',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Clear existing data
            self.league = SeededLadderLeague()
            
            # Player names
            names = [
                "Alex Martinez", "Blake Johnson", "Casey Williams", "Drew Anderson",
                "Emma Thompson", "Frank Garcia", "Grace Miller", "Henry Davis",
                "Iris Rodriguez", "Jack Wilson", "Kelly Moore", "Logan Taylor",
                "Maya Jackson", "Noah White", "Olivia Harris", "Parker Martin",
                "Quinn Roberts", "Riley Cooper", "Sam Peterson", "Taylor Brooks"
            ]
            
            # Add players based on count
            for i in range(min(count, len(names))):
                self.league.add_player(names[i])
            
            # Start in seeding session mode - players are NOT pre-assigned to tiers
            # They will be assigned after the first seeding session
            self.league.is_seeding_session = True
            
            # Set appropriate court assignments based on count
            if count == 12:
                # 3 players per tier - use 3 courts
                self.league.tier_court_assignments = {
                    1: [4],
                    2: [3],
                    3: [2],
                    4: [1]
                }
            elif count == 20:
                # 5 players per tier - use multiple courts for Tier 1 and 2
                self.league.tier_court_assignments = {
                    1: [3, 4],
                    2: [1, 2],
                    3: [2],
                    4: [1]
                }
            else:
                # Default for 16 or other counts
                self.league.tier_court_assignments = {
                    1: [4],
                    2: [3],
                    3: [2],
                    4: [1]
                }
            
            # Update all UI
            self.update_players_list()
            self.update_player_numbers_table()
            self.update_scores_player_numbers()
            self.update_rounds_display()
            self.update_scores_table()
            self.update_rankings()
            self.update_session_info()
            self.update_history_list()
            
            # Update tier court inputs if they exist
            if hasattr(self, 'tier_court_inputs'):
                for tier_num, input_field in self.tier_court_inputs.items():
                    courts = self.league.tier_court_assignments.get(tier_num, [])
                    input_field.setText(','.join(map(str, courts)))
            
            self.save_data()
            self.status_label.setText(f'Loaded {count} demo players with tier assignments')
    
    def update_players_list(self):
        self.players_list.clear()
        
        # Sort by Tier then Name
        sorted_players = sorted(self.league.players, key=lambda p: (self.league.player_tiers.get(p, 4), p))
        
        for player in sorted_players:
            tier = self.league.player_tiers.get(player, 4)
            tier_names = {1: "Tier 1 (Top)", 2: "Tier 2", 3: "Tier 3", 4: "Tier 4"}
            tier_str = tier_names.get(tier, f"Tier {tier}")
            player_num = self.league.player_numbers.get(player, '?')
            self.players_list.addItem(f"#{player_num} - {player} ({tier_str})")
        
        num_courts = self.league.get_active_courts()
        self.status_label.setText(f'Total players: {len(self.league.players)} | Active courts: {num_courts}')
    
    def update_player_numbers_table(self):
        # Sort players by their assigned number
        sorted_players = sorted(self.league.players, key=lambda p: self.league.player_numbers.get(p, 999))
        
        self.player_numbers_table.setRowCount(len(sorted_players))
        
        for i, player in enumerate(sorted_players):
            player_num = self.league.player_numbers.get(player, '?')
            
            num_item = QTableWidgetItem(f"#{player_num}")
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_font = QFont()
            num_font.setBold(True)
            num_font.setPointSize(11)
            num_item.setFont(num_font)
            self.player_numbers_table.setItem(i, 0, num_item)
            
            name_item = QTableWidgetItem(player)
            self.player_numbers_table.setItem(i, 1, name_item)
            
            tier = self.league.player_tiers.get(player, 4)
            tier_str = f"Tier {tier}"
            tier_item = QTableWidgetItem(tier_str)
            tier_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if tier == 1:
                tier_item.setForeground(QColor('green'))
                tier_font = QFont()
                tier_font.setBold(True)
                tier_item.setFont(tier_font)
            elif tier == 2:
                tier_item.setForeground(QColor('blue'))
            self.player_numbers_table.setItem(i, 2, tier_item)
    
    def update_scores_player_numbers(self):
        # Sort players by their assigned number
        sorted_players = sorted(self.league.players, key=lambda p: self.league.player_numbers.get(p, 999))
        
        self.scores_player_numbers_table.setRowCount(len(sorted_players))
        
        for i, player in enumerate(sorted_players):
            player_num = self.league.player_numbers.get(player, '?')
            
            num_item = QTableWidgetItem(f"#{player_num}")
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_font = QFont()
            num_font.setBold(True)
            num_font.setPointSize(10)
            num_item.setFont(num_font)
            self.scores_player_numbers_table.setItem(i, 0, num_item)
            
            name_item = QTableWidgetItem(player)
            self.scores_player_numbers_table.setItem(i, 1, name_item)
            
            tier = self.league.player_tiers.get(player, 4)
            tier_str = f"Tier {tier}"
            tier_item = QTableWidgetItem(tier_str)
            tier_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if tier == 1:
                tier_item.setForeground(QColor('green'))
                tier_font = QFont()
                tier_font.setBold(True)
                tier_item.setFont(tier_font)
            elif tier == 2:
                tier_item.setForeground(QColor('blue'))
            self.scores_player_numbers_table.setItem(i, 2, tier_item)
    
    def save_court_assignments(self):
        """Save the configured tier-to-court assignments"""
        try:
            new_assignments = {}
            for tier_num, input_field in self.tier_court_inputs.items():
                court_text = input_field.text().strip()
                if court_text:
                    # Parse comma-separated court numbers
                    courts = [int(c.strip()) for c in court_text.split(',') if c.strip().isdigit()]
                    new_assignments[tier_num] = courts
                else:
                    new_assignments[tier_num] = []
            
            # Update the league's court assignments
            self.league.tier_court_assignments = new_assignments
            
            # Save to file
            self.league.save_to_file(self.data_file)
            
            # Update display
            self.update_rounds_display()
            
            QMessageBox.information(self, 'Success', 'Court assignments saved successfully!')
            self.status_label.setText('Court assignments updated')
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Failed to save court assignments: {str(e)}')
    
    def reset_court_assignments(self):
        """Reset tier-to-court assignments to default"""
        reply = QMessageBox.question(self, 'Reset to Default', 
                                     'Reset court assignments to default?\n\nTier 1: Court 4\nTier 2: Court 3\nTier 3: Court 2\nTier 4: Court 1',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Reset to default
            self.league.tier_court_assignments = {
                1: [4],
                2: [3],
                3: [2],
                4: [1]
            }
            
            # Update input fields
            for tier_num, input_field in self.tier_court_inputs.items():
                courts = self.league.tier_court_assignments.get(tier_num, [])
                input_field.setText(','.join(map(str, courts)))
            
            # Save to file
            self.league.save_to_file(self.data_file)
            
            QMessageBox.information(self, 'Success', 'Court assignments reset to default!')
            self.status_label.setText('Court assignments reset to default')
    
    def open_big_screen(self):
        if not self.league.session_rounds:
            QMessageBox.warning(self, 'No Rounds', 'Please generate a round first before opening the big screen display.')
            return
        
        self.big_screen = BigScreenDisplay(self.league, self)
        self.big_screen.show()
    
    def generate_round(self):
        round_data, error = self.league.generate_round()
        
        if error:
            QMessageBox.warning(self, 'Cannot Generate Round', error)
            return
        
        self.update_rounds_display()
        self.update_scores_table()
        self.save_data()
        self.status_label.setText(f'Round {round_data["round_number"]} generated!')
    
    def simulate_scores(self):
        """Simulate random scores for all pending games in current session"""
        if not self.league.session_rounds:
            QMessageBox.warning(self, 'No Rounds', 'No rounds to simulate scores for.')
            return
            
        count = 0
        for round_idx, round_data in enumerate(self.league.session_rounds, 1):
            for court in round_data['courts']:
                if not court.get('completed', False):
                    # Generate random realistic scores (e.g. 11-5, 11-9, 13-11)
                    if random.random() > 0.5:
                        s1, s2 = 11, random.randint(0, 9)
                    else:
                        s1, s2 = random.randint(0, 9), 11
                    
                    # Record the score
                    self.league.record_game_score(round_idx, court['court'], s1, s2, court['team1'], court['team2'])
                    count += 1
        
        if count > 0:
            self.update_scores_table()
            self.update_rounds_display()
            self.update_rankings()
            self.save_data()
            self.status_label.setText(f'Simulated scores for {count} games')
            QMessageBox.information(self, 'Simulation Complete', f'Successfully simulated scores for {count} pending games.')
        else:
            QMessageBox.information(self, 'No Pending Games', 'All games are already completed.')
    
    def update_rounds_display(self):
        output = ''
        
        for round_data in self.league.session_rounds:
            round_num = round_data['round_number']
            output += f'\n{"=" * 60}\n'
            output += f'ROUND {round_num}\n'
            output += f'{"=" * 60}\n\n'
            
            for court in round_data['courts']:
                output += f'COURT {court["court"]}:\n'
                # Add player numbers to team display
                t1p1_num = self.league.player_numbers.get(court["team1"][0], '?')
                t1p2_num = self.league.player_numbers.get(court["team1"][1], '?')
                t2p1_num = self.league.player_numbers.get(court["team2"][0], '?')
                t2p2_num = self.league.player_numbers.get(court["team2"][1], '?')
                output += f'  Team 1: #{t1p1_num} {court["team1"][0]} & #{t1p2_num} {court["team1"][1]}\n'
                output += f'  Team 2: #{t2p1_num} {court["team2"][0]} & #{t2p2_num} {court["team2"][1]}\n'
                if court['completed']:
                    output += f'  Score: {court["team1_score"]} - {court["team2_score"]}\n'
                output += '\n'
            
            if round_data['sitting_players']:
                sitting_with_nums = [f"#{self.league.player_numbers.get(p, '?')} {p}" for p in round_data["sitting_players"]]
                output += f'Sitting out: {", ".join(sitting_with_nums)}\n'
        
        self.rounds_display.setText(output)
        self.round_count_label.setText(f'Rounds: {len(self.league.session_rounds)}')
    
    def update_scores_table(self):
        self.scores_table.setRowCount(0)
        
        for round_data in self.league.session_rounds:
            round_num = round_data['round_number']
            for court in round_data['courts']:
                row = self.scores_table.rowCount()
                self.scores_table.insertRow(row)
                
                self.scores_table.setItem(row, 0, QTableWidgetItem(str(round_num)))
                self.scores_table.setItem(row, 1, QTableWidgetItem(str(court['court'])))
                # Add player numbers to scores table
                t1p1_num = self.league.player_numbers.get(court['team1'][0], '?')
                t1p2_num = self.league.player_numbers.get(court['team1'][1], '?')
                t2p1_num = self.league.player_numbers.get(court['team2'][0], '?')
                t2p2_num = self.league.player_numbers.get(court['team2'][1], '?')
                self.scores_table.setItem(row, 2, QTableWidgetItem(f"#{t1p1_num} {court['team1'][0]} & #{t1p2_num} {court['team1'][1]}"))
                self.scores_table.setItem(row, 3, QTableWidgetItem(f"#{t2p1_num} {court['team2'][0]} & #{t2p2_num} {court['team2'][1]}"))
                
                if court['completed']:
                    score_text = f"{court['team1_score']} - {court['team2_score']}"
                    self.scores_table.setItem(row, 4, QTableWidgetItem(score_text))
                    self.scores_table.setItem(row, 5, QTableWidgetItem('Completed'))
                else:
                    self.scores_table.setItem(row, 4, QTableWidgetItem(''))
                    enter_btn = QPushButton('Enter Score')
                    enter_btn.clicked.connect(lambda checked, r=round_num, c=court['court'], 
                                             t1=court['team1'], t2=court['team2']: 
                                             self.enter_score(r, c, t1, t2))
                    self.scores_table.setCellWidget(row, 5, enter_btn)
    
    def enter_score(self, round_num, court_num, team1, team2):
        dialog = ScoreDialog(round_num, court_num, team1, team2, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            team1_score, team2_score = dialog.get_scores()
            if self.league.record_game_score(round_num, court_num, team1_score, team2_score, team1, team2):
                self.update_scores_table()
                self.update_rounds_display()
                self.update_rankings()
                self.save_data()
                self.status_label.setText(f'Score recorded: Round {round_num}, Court {court_num}')
    
    def update_rankings(self):
        rankings = self.league.get_rankings()
        
        self.rankings_table.setRowCount(len(rankings))
        
        for i, rank_data in enumerate(rankings):
            self.rankings_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.rankings_table.setItem(i, 1, QTableWidgetItem(str(rank_data['tier'])))
            # Add player number to rankings
            player_num = self.league.player_numbers.get(rank_data['player'], '?')
            self.rankings_table.setItem(i, 2, QTableWidgetItem(f"#{player_num} {rank_data['player']}"))
            self.rankings_table.setItem(i, 3, QTableWidgetItem(str(rank_data['games_played'])))
            self.rankings_table.setItem(i, 4, QTableWidgetItem(str(rank_data['points'])))
            
            diff = rank_data['differential']
            diff_text = f"+{diff}" if diff > 0 else str(diff)
            diff_item = QTableWidgetItem(diff_text)
            if diff > 0:
                diff_item.setForeground(QColor('green'))
            elif diff < 0:
                diff_item.setForeground(QColor('red'))
            self.rankings_table.setItem(i, 5, diff_item)
        
        # Update last session rankings
        self.update_last_session_rankings()
    
    def update_last_session_rankings(self):
        """Populate the last session rankings table"""
        self.last_session_table.setRowCount(0)
        
        if not self.league.session_history:
            return
        
        last_session = self.league.session_history[-1]
        last_rankings = last_session.get('rankings', [])
        
        self.last_session_table.setRowCount(len(last_rankings))
        
        for i, rank_data in enumerate(last_rankings):
            self.last_session_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.last_session_table.setItem(i, 1, QTableWidgetItem(str(rank_data.get('tier', '?'))))
            player_num = self.league.player_numbers.get(rank_data['player'], '?')
            self.last_session_table.setItem(i, 2, QTableWidgetItem(f"#{player_num} {rank_data['player']}"))
            self.last_session_table.setItem(i, 3, QTableWidgetItem(str(rank_data.get('points', 0))))
            
            diff = rank_data.get('differential', 0)
            diff_text = f"+{diff}" if diff > 0 else str(diff)
            diff_item = QTableWidgetItem(diff_text)
            if diff > 0:
                diff_item.setForeground(QColor('green'))
            elif diff < 0:
                diff_item.setForeground(QColor('red'))
            self.last_session_table.setItem(i, 4, diff_item)
    
    def update_session_info(self):
        info = f'Session #{self.league.current_session}\n'
        info += f'Status: {"Seeding Session (Mixed)" if self.league.is_seeding_session else "Tiered Session (Ranked)"}\n'
        info += f'Total Rounds: {len(self.league.session_rounds)}\n'
        info += f'Players: {len(self.league.players)}\n'
        info += f'Active Courts: {self.league.get_active_courts()}\n'
        
        if not self.league.is_seeding_session:
            t1_count = len(self.league.get_tier_players(1))
            t2_count = len(self.league.get_tier_players(2))
            info += f'Tier 1 Players (Courts 2,3): {t1_count}\n'
            info += f'Tier 2 Players (Courts 1,4): {t2_count}\n'
            
        self.session_info.setText(info)
        
        # Update title if status changes
        title_text = 'Seeded Ladder League Manager'
        if self.league.is_seeding_session:
            title_text += ' (Seeding Session)'
        else:
            title_text += ' (Tiered Play)'
        self.title_label.setText(title_text)
        
        # Update Rounds tab label
        mode_text = "Seeding Mode: Everyone plays everyone (Random)" if self.league.is_seeding_session else "Tiered Mode: Top Tier on Courts 2&3, Lower Tier on Courts 1&4"
        self.rounds_info_label.setText(f'{mode_text}\nGenerate rounds for your session.')

    def update_history_list(self):
        self.history_list.clear()
        for session in reversed(self.league.session_history):
            mode = "Seeding" if session.get('is_seeding', False) else "Tiered"
            item_text = f"Session #{session['session_number']} ({mode}) - {session['date']} ({session['player_count']} players)"
            self.history_list.addItem(item_text)

    def show_history_details(self, item):
        session_num = int(item.text().split('#')[1].split(' ')[0])
        session = None
        for s in self.league.session_history:
            if s['session_number'] == session_num:
                session = s
                break
        
        if not session:
            return
        
        details = f"SESSION #{session['session_number']}\n"
        details += f"Mode: {'Seeding' if session.get('is_seeding') else 'Tiered'}\n"
        details += f"Date: {session['date']}\n"
        
        if 'seeded_tier1' in session and session['seeded_tier1']:
            details += f"\nSEEDS ASSIGNED AFTER THIS SESSION:\n"
            details += f"Tier 1: {', '.join(session['seeded_tier1'])}\n"
            if 'seeded_tier2' in session and session['seeded_tier2']:
                details += f"Tier 2: {', '.join(session['seeded_tier2'])}\n"
            if 'seeded_tier3' in session and session['seeded_tier3']:
                details += f"Tier 3: {', '.join(session['seeded_tier3'])}\n"
            if 'seeded_tier4' in session and session['seeded_tier4']:
                details += f"Tier 4: {', '.join(session['seeded_tier4'])}\n"
        
        if 'promoted' in session and session['promoted']:
            details += f"\nPROMOTIONS:\n"
            for player, from_tier, to_tier in session['promoted']:
                details += f"  {player}: Tier {from_tier} → Tier {to_tier}\n"
        if 'relegated' in session and session['relegated']:
            details += f"\nRELEGATIONS:\n"
            for player, from_tier, to_tier in session['relegated']:
                details += f"  {player}: Tier {from_tier} → Tier {to_tier}\n"
            
        details += "\n" + "=" * 60 + "\n"
        details += "FINAL RANKINGS\n"
        details += "=" * 60 + "\n\n"
        
        for i, rank in enumerate(session['rankings'], 1):
            details += f"{i}. {rank['player']} (Tier {rank.get('tier', '?')})\n"
            details += f"   Points: {rank['points']} (from {rank['counted_games']} games)\n"
            details += f"   Differential: {rank['differential']:+d}\n\n"
        
        self.history_details.setText(details)

    def new_session(self):
        msg = 'End current session and start a new one?\n\n'
        if self.league.is_seeding_session:
            msg += 'This will finalize SEEDING. Players will be divided into 4 tiers for next session.\n'
        else:
            msg += 'This will process PROMOTION/RELEGATION between all 4 tiers based on results.\n'
            
        reply = QMessageBox.question(self, 'Start New Session', 
                                     msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Capture rankings before they are reset
            final_rankings = self.league.get_rankings()
            
            # Run the new session logic (which updates tiers and resets stats)
            self.league.new_session()
            
            # Show summary of what just happened
            summary = "SESSION COMPLETE!\n\n"
            summary += "Final Rankings & Changes:\n"
            summary += "=" * 50 + "\n\n"
            
            # Get the session data we just saved to history
            if self.league.session_history:
                last_session = self.league.session_history[-1]
                
                # Show promotions/relegations/seeds
                if last_session.get('is_seeding'):
                    summary += "SEEDS ASSIGNED:\n"
                    if last_session.get('seeded_tier1'):
                        summary += f"Tier 1: {', '.join(last_session['seeded_tier1'])}\n"
                    if last_session.get('seeded_tier2'):
                        summary += f"Tier 2: {', '.join(last_session['seeded_tier2'])}\n"
                    if last_session.get('seeded_tier3'):
                        summary += f"Tier 3: {', '.join(last_session['seeded_tier3'])}\n"
                    if last_session.get('seeded_tier4'):
                        summary += f"Tier 4: {', '.join(last_session['seeded_tier4'])}\n"
                    summary += "\n"
                else:
                    if last_session.get('promoted'):
                        summary += "PROMOTED:\n"
                        for p, from_t, to_t in last_session['promoted']:
                            summary += f"  {p}: Tier {from_t} → Tier {to_t}\n"
                        summary += "\n"
                    
                    if last_session.get('relegated'):
                        summary += "RELEGATED:\n"
                        for p, from_t, to_t in last_session['relegated']:
                            summary += f"  {p}: Tier {from_t} → Tier {to_t}\n"
                        summary += "\n"
                
                summary += "FINAL STANDINGS:\n"
                for i, rank in enumerate(final_rankings, 1):
                    # For seeding session, we don't have tiers yet in the ranking object from BEFORE the session end
                    # But for tiered session, we want to show the tier they played in
                    tier_display = f"(Tier {rank.get('tier', '?')})" if not last_session.get('is_seeding') else ""
                    summary += f"{i}. {rank['player']} {tier_display}\n"
                    summary += f"   Points: {rank['points']} | Diff: {rank['differential']:+d}\n"
            
            # Show the summary dialog
            summary_dialog = QMessageBox(self)
            summary_dialog.setWindowTitle("Session Summary")
            summary_dialog.setText("Session finalized. Here are the results:")
            summary_dialog.setDetailedText(summary)
            summary_dialog.setIcon(QMessageBox.Icon.Information)
            summary_dialog.exec()
            
            # Now update the UI for the new session
            self.update_players_list()
            self.update_player_numbers_table()
            self.update_scores_player_numbers()
            self.update_rounds_display()
            self.update_scores_table()
            self.update_rankings()
            self.update_session_info()
            self.update_history_list()
            self.save_data()
            
            status = "Seeding Complete! Tiers Assigned." if not self.league.is_seeding_session and self.league.current_session == 2 else "New Session Started"
            self.status_label.setText(status)

    def reset_all_data(self):
        reply = QMessageBox.question(self, 'Reset All Data',
                                     'Reset ALL data? Players will be kept but set to unseeded.\n\nAre you sure?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.league.reset_all()
            self.update_players_list()
            self.update_rounds_display()
            self.update_scores_table()
            self.update_rankings()
            self.update_session_info()
            self.update_history_list()
            self.save_data()
            self.status_label.setText('All data reset')
    
    def clear_all_data(self):
        reply = QMessageBox.warning(self, 'Clear ALL Data',
                                    '⚠️ WARNING: This will DELETE EVERYTHING!\n\n'
                                    '• All players will be removed\n'
                                    '• All rounds and scores will be deleted\n'
                                    '• All session history will be erased\n'
                                    '• All tier assignments will be cleared\n'
                                    '• Court assignments will be reset to default\n\n'
                                    'This action CANNOT be undone!\n\n'
                                    'Are you absolutely sure?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Double confirmation
            confirm = QMessageBox.question(self, 'Final Confirmation',
                                          'Last chance! Delete everything?',
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                          QMessageBox.StandardButton.No)
            
            if confirm == QMessageBox.StandardButton.Yes:
                # Create a fresh league instance
                self.league = SeededLadderLeague()
                
                # Update all UI elements
                self.update_players_list()
                self.update_player_numbers_table()
                self.update_scores_player_numbers()
                self.update_rounds_display()
                self.update_scores_table()
                self.update_rankings()
                self.update_session_info()
                self.update_history_list()
                
                # Save the empty state
                self.save_data()
                
                QMessageBox.information(self, 'Data Cleared', 'All data has been completely cleared.')
                self.status_label.setText('All data cleared - starting fresh')

    def save_data(self):
        self.league.save_to_file(self.data_file)
    
    def closeEvent(self, event):
        self.save_data()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
