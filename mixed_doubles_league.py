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
                             QFormLayout, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont, QColor


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class MixedDoublesLeague:
    def __init__(self):
        self.teams = []  # List of team dicts: {'name': str, 'player1': str, 'player2': str}
        self.session_rounds = []
        self.current_session = 1
        self.team_stats = {}  # Stats keyed by team name
        self.session_history = []
        self.team_numbers = {}  # Map team name to assigned number
        self.next_team_number = 1  # Track next available number
        
    def add_team(self, player1, player2):
        """Add a doubles team - team name is auto-generated from players"""
        if not player1 or not player2:
            return False
        
        # Auto-generate team name from player names
        team_name = f"{player1} & {player2}"
        
        # Check if this exact pairing already exists
        if team_name in [t['name'] for t in self.teams]:
            return False
            
        team = {
            'name': team_name,
            'player1': player1,
            'player2': player2
        }
        self.teams.append(team)
        self.team_stats[team_name] = {
            'games_played': 0,
            'wins': 0,
            'losses': 0,
            'total_points': 0,
            'total_points_against': 0,
            'rounds_sat_out': 0,
            'last_sat_out_round': -2,
            'game_scores': []
        }
        # Assign team number
        self.team_numbers[team_name] = self.next_team_number
        self.next_team_number += 1
        return True
    
    def remove_team(self, team_name):
        """Remove a team"""
        for team in self.teams:
            if team['name'] == team_name:
                self.teams.remove(team)
                if team_name in self.team_stats:
                    del self.team_stats[team_name]
                if team_name in self.team_numbers:
                    del self.team_numbers[team_name]
                return True
        return False
    
    def get_active_courts(self):
        """Determine number of courts based on team count"""
        team_count = len(self.teams)
        
        if team_count >= 8:
            return 4
        elif team_count >= 6:
            return 3
        elif team_count >= 4:
            return 2
        else:
            return 1
    
    def get_teams_per_round(self):
        """Calculate how many teams play each round (2 teams per court)"""
        return self.get_active_courts() * 2
    
    def can_sit_out(self, team_name, current_round_num):
        """Check if team can sit out this round (didn't sit out last round)"""
        last_sat = self.team_stats[team_name]['last_sat_out_round']
        return (current_round_num - last_sat) > 1
    
    def get_games_played(self, team_name):
        """Get number of games played by team"""
        return self.team_stats[team_name]['games_played']
    
    def select_sitting_teams(self, current_round_num):
        """Select teams to sit out, prioritizing those who haven't sat recently and have more games"""
        num_courts = self.get_active_courts()
        teams_per_round = num_courts * 2
        num_sitting = len(self.teams) - teams_per_round
        
        if num_sitting <= 0:
            return []
        
        # Score each team for sitting priority
        sit_scores = []
        for team in self.teams:
            team_name = team['name']
            if not self.can_sit_out(team_name, current_round_num):
                continue
            
            games_played = self.get_games_played(team_name)
            rounds_sat = self.team_stats[team_name]['rounds_sat_out']
            last_sat = self.team_stats[team_name]['last_sat_out_round']
            
            # Higher score = more likely to sit
            score = games_played * 10 - rounds_sat * 20 + (current_round_num - last_sat)
            sit_scores.append((team_name, score))
        
        # Sort by score (highest first) and select top num_sitting
        sit_scores.sort(key=lambda x: x[1], reverse=True)
        sitting_teams = [t for t, _ in sit_scores[:num_sitting]]
        
        # If we don't have enough eligible teams, force some to sit
        if len(sitting_teams) < num_sitting:
            remaining = [t['name'] for t in self.teams if t['name'] not in sitting_teams]
            random.shuffle(remaining)
            sitting_teams.extend(remaining[:num_sitting - len(sitting_teams)])
        
        return sitting_teams
    
    def generate_round(self):
        """Generate a new round with proper sit-out rotation"""
        num_courts = self.get_active_courts()
        
        if len(self.teams) < num_courts * 2:
            return None, f"Need at least {num_courts * 2} teams for {num_courts} courts"
        
        current_round_num = len(self.session_rounds) + 1
        
        # Select which teams sit out
        sitting_teams = self.select_sitting_teams(current_round_num)
        
        # Get playing teams
        playing_teams = [t for t in self.teams if t['name'] not in sitting_teams]
        random.shuffle(playing_teams)
        
        # Assign to courts (2 teams per court)
        courts = []
        for court_num in range(1, num_courts + 1):
            start_idx = (court_num - 1) * 2
            court_teams = playing_teams[start_idx:start_idx + 2]
            
            if len(court_teams) == 2:
                courts.append({
                    'court': court_num,
                    'team1': court_teams[0],
                    'team2': court_teams[1],
                    'team1_score': 0,
                    'team2_score': 0,
                    'completed': False
                })
        
        # Update sit-out tracking
        for team_name in sitting_teams:
            self.team_stats[team_name]['rounds_sat_out'] += 1
            self.team_stats[team_name]['last_sat_out_round'] = current_round_num
        
        round_data = {
            'round_number': current_round_num,
            'courts': courts,
            'sitting_teams': sitting_teams
        }
        
        self.session_rounds.append(round_data)
        return round_data, None
    
    def record_game_score(self, round_num, court_num, team1_score, team2_score):
        """Record scores for a completed game"""
        if round_num < 1 or round_num > len(self.session_rounds):
            return False
        
        round_data = self.session_rounds[round_num - 1]
        court = None
        for c in round_data['courts']:
            if c['court'] == court_num:
                court = c
                break
        
        if not court or court['completed']:
            return False
        
        court['team1_score'] = team1_score
        court['team2_score'] = team2_score
        court['completed'] = True
        
        # Update team stats
        team1_name = court['team1']['name']
        team2_name = court['team2']['name']
        
        self.team_stats[team1_name]['games_played'] += 1
        self.team_stats[team1_name]['total_points'] += team1_score
        self.team_stats[team1_name]['total_points_against'] += team2_score
        
        self.team_stats[team2_name]['games_played'] += 1
        self.team_stats[team2_name]['total_points'] += team2_score
        self.team_stats[team2_name]['total_points_against'] += team1_score
        
        # Record wins/losses
        if team1_score > team2_score:
            self.team_stats[team1_name]['wins'] += 1
            self.team_stats[team2_name]['losses'] += 1
        else:
            self.team_stats[team2_name]['wins'] += 1
            self.team_stats[team1_name]['losses'] += 1
        
        # Store game score
        self.team_stats[team1_name]['game_scores'].append({
            'round': round_num,
            'opponent': team2_name,
            'score_for': team1_score,
            'score_against': team2_score
        })
        self.team_stats[team2_name]['game_scores'].append({
            'round': round_num,
            'opponent': team1_name,
            'score_for': team2_score,
            'score_against': team1_score
        })
        
        return True
    
    def get_rankings(self):
        """Get team rankings based on wins and point differential"""
        rankings = []
        
        for team in self.teams:
            team_name = team['name']
            stats = self.team_stats[team_name]
            
            differential = stats['total_points'] - stats['total_points_against']
            win_percentage = (stats['wins'] / stats['games_played'] * 100) if stats['games_played'] > 0 else 0
            
            rankings.append({
                'team': team_name,
                'player1': team['player1'],
                'player2': team['player2'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'win_pct': win_percentage,
                'points': stats['total_points'],
                'points_against': stats['total_points_against'],
                'differential': differential,
                'games_played': stats['games_played']
            })
        
        # Sort by wins (descending), then differential (descending)
        rankings.sort(key=lambda x: (x['wins'], x['differential']), reverse=True)
        
        return rankings
    
    def new_session(self):
        """Start a new session, saving current session to history but keeping cumulative stats"""
        # Save current session to history if it has rounds
        if self.session_rounds:
            session_data = {
                'session_number': self.current_session,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'rounds': self.session_rounds,
                'rankings': self.get_rankings(),
                'team_count': len(self.teams)
            }
            self.session_history.append(session_data)
        
        # Clear current session rounds but KEEP cumulative stats (no ladder/tiers)
        self.session_rounds = []
        # Only reset sit-out tracking for new session, keep points/wins cumulative
        for team in self.teams:
            team_name = team['name']
            self.team_stats[team_name]['rounds_sat_out'] = 0
            self.team_stats[team_name]['last_sat_out_round'] = -2
        self.current_session += 1
    
    def clear_current_session(self):
        """Clear current session rounds and scores without saving to history"""
        self.session_rounds = []
        for team in self.teams:
            team_name = team['name']
            self.team_stats[team_name] = {
                'games_played': 0,
                'wins': 0,
                'losses': 0,
                'total_points': 0,
                'total_points_against': 0,
                'rounds_sat_out': 0,
                'last_sat_out_round': -2,
                'game_scores': []
            }
    
    def clear_history(self):
        """Clear all session history"""
        self.session_history = []
    
    def reset_all(self):
        """Reset everything except teams"""
        self.session_rounds = []
        self.current_session = 1
        self.session_history = []
        for team in self.teams:
            team_name = team['name']
            self.team_stats[team_name] = {
                'games_played': 0,
                'wins': 0,
                'losses': 0,
                'total_points': 0,
                'total_points_against': 0,
                'rounds_sat_out': 0,
                'last_sat_out_round': -2,
                'game_scores': []
            }
    
    def clear_all_data(self):
        """Clear everything including teams"""
        self.teams = []
        self.session_rounds = []
        self.current_session = 1
        self.team_stats = {}
        self.session_history = []
        self.team_numbers = {}
        self.next_team_number = 1
    
    def save_to_file(self, filename):
        data = {
            'teams': self.teams,
            'session_rounds': self.session_rounds,
            'current_session': self.current_session,
            'team_stats': self.team_stats,
            'session_history': self.session_history,
            'team_numbers': self.team_numbers,
            'next_team_number': self.next_team_number
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filename):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                self.teams = data.get('teams', [])
                self.session_rounds = data.get('session_rounds', [])
                self.current_session = data.get('current_session', 1)
                self.team_stats = data.get('team_stats', {})
                self.session_history = data.get('session_history', [])
                self.team_numbers = data.get('team_numbers', {})
                self.next_team_number = data.get('next_team_number', 1)
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
        
        # Title, round number, and date/time
        title_container = QVBoxLayout()
        self.title_label = QLabel('CURRENT ROUND')
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(int(self.screen_height * 0.035))
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #00d4ff;")
        title_container.addWidget(self.title_label)
        
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
        
        # Sitting teams at bottom
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
        
        # Clear existing courts
        self.clear_courts()
        
        # Display each court
        for court_data in current_round['courts']:
            court_widget = self.create_court_widget(court_data)
            self.courts_layout.addWidget(court_widget)
        
        # Display sitting teams
        if current_round.get('sitting_teams'):
            sitting_text = "SITTING OUT: " + " • ".join([
                f"#{self.league.team_numbers.get(team_name, '?')} {team_name}" 
                for team_name in current_round['sitting_teams']
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
        
        # Court number - compact sizing
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
        
        # Team 1
        team1_num = self.league.team_numbers.get(court_data['team1']['name'], '?')
        team1_label = QLabel(f"#{team1_num}  {court_data['team1']['player1']} & {court_data['team1']['player2']}")
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
        
        # Team 2
        team2_num = self.league.team_numbers.get(court_data['team2']['name'], '?')
        team2_label = QLabel(f"#{team2_num}  {court_data['team2']['player1']} & {court_data['team2']['player2']}")
        team2_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        team2_label.setFont(name_font)
        team2_label.setStyleSheet("color: #f39c12; padding: 5px;")
        teams_layout.addWidget(team2_label, 1)
        
        layout.addLayout(teams_layout, 1)
        
        # Score (if completed)
        if court_data['completed']:
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
        
        team1_label = QLabel(f"Team 1: {team1['name']}")
        team1_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        form.addRow(team1_label)
        
        players1_label = QLabel(f"   {team1['player1']} & {team1['player2']}")
        form.addRow(players1_label)
        
        self.team1_score = QSpinBox()
        self.team1_score.setRange(0, 99)
        self.team1_score.setValue(11)
        form.addRow("Team 1 Score:", self.team1_score)
        
        form.addRow(QLabel(""))
        
        team2_label = QLabel(f"Team 2: {team2['name']}")
        team2_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        form.addRow(team2_label)
        
        players2_label = QLabel(f"   {team2['player1']} & {team2['player2']}")
        form.addRow(players2_label)
        
        self.team2_score = QSpinBox()
        self.team2_score.setRange(0, 99)
        self.team2_score.setValue(9)
        form.addRow("Team 2 Score:", self.team2_score)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_scores(self):
        return self.team1_score.value(), self.team2_score.value()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.league = MixedDoublesLeague()
        self.data_file = Path('mixed_doubles_data.json')
        
        if self.data_file.exists():
            self.league.load_from_file(self.data_file)
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('ROC City Pickleball - Doubles League Manager')
        self.setGeometry(100, 100, 1200, 800)
        
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
        
        title_label = QLabel('Doubles League Manager')
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        subtitle_label = QLabel('Teams Stay Together')
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_font.setItalic(True)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle_label)
        
        self.status_label = QLabel('Ready')
        main_layout.addWidget(self.status_label)
        
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        tabs.addTab(self.create_teams_tab(), 'Teams')
        tabs.addTab(self.create_team_numbers_tab(), 'Team Numbers')
        tabs.addTab(self.create_rounds_tab(), 'Rounds')
        tabs.addTab(self.create_scores_tab(), 'Enter Scores')
        tabs.addTab(self.create_rankings_tab(), 'Rankings')
        tabs.addTab(self.create_history_tab(), 'History')
        tabs.addTab(self.create_session_tab(), 'Session')
    
    def create_teams_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        add_group = QGroupBox('Add Doubles Team')
        add_layout = QVBoxLayout()
        
        info_label = QLabel('Enter both player names (team name will be auto-generated)')
        info_label.setStyleSheet('font-style: italic; color: #666;')
        add_layout.addWidget(info_label)
        
        player1_layout = QHBoxLayout()
        player1_layout.addWidget(QLabel('Player 1:'))
        self.player1_input = QLineEdit()
        self.player1_input.setPlaceholderText('First player name')
        self.player1_input.returnPressed.connect(lambda: self.player2_input.setFocus())
        player1_layout.addWidget(self.player1_input)
        add_layout.addLayout(player1_layout)
        
        player2_layout = QHBoxLayout()
        player2_layout.addWidget(QLabel('Player 2:'))
        self.player2_input = QLineEdit()
        self.player2_input.setPlaceholderText('Second player name')
        self.player2_input.returnPressed.connect(self.add_team)
        player2_layout.addWidget(self.player2_input)
        add_layout.addLayout(player2_layout)
        
        add_btn = QPushButton('Add Team')
        add_btn.clicked.connect(self.add_team)
        add_btn.setStyleSheet('QPushButton { background-color: #4CAF50; color: white; padding: 8px; }')
        add_layout.addWidget(add_btn)
        
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)
        
        teams_group = QGroupBox('Current Teams')
        teams_layout = QVBoxLayout()
        
        self.teams_list = QListWidget()
        self.update_teams_list()
        teams_layout.addWidget(self.teams_list)
        
        remove_btn = QPushButton('Remove Selected Team')
        remove_btn.clicked.connect(self.remove_team)
        remove_btn.setStyleSheet('QPushButton { background-color: #f44336; color: white; padding: 8px; }')
        teams_layout.addWidget(remove_btn)
        
        teams_group.setLayout(teams_layout)
        layout.addWidget(teams_group)
        
        demo_group = QGroupBox('Demo Teams')
        demo_layout = QHBoxLayout()
        
        demo_8_btn = QPushButton('8 Teams\n(4 courts)')
        demo_8_btn.clicked.connect(lambda: self.load_demo_teams(8))
        demo_8_btn.setStyleSheet('QPushButton { background-color: #2196F3; color: white; padding: 8px; }')
        demo_layout.addWidget(demo_8_btn)
        
        demo_6_btn = QPushButton('6 Teams\n(3 courts)')
        demo_6_btn.clicked.connect(lambda: self.load_demo_teams(6))
        demo_6_btn.setStyleSheet('QPushButton { background-color: #2196F3; color: white; padding: 8px; }')
        demo_layout.addWidget(demo_6_btn)
        
        demo_10_btn = QPushButton('10 Teams\n(4 courts + sitouts)')
        demo_10_btn.clicked.connect(lambda: self.load_demo_teams(10))
        demo_10_btn.setStyleSheet('QPushButton { background-color: #2196F3; color: white; padding: 8px; }')
        demo_layout.addWidget(demo_10_btn)
        
        demo_3_btn = QPushButton('3 Teams\n(1-2 courts)')
        demo_3_btn.clicked.connect(lambda: self.load_demo_teams(3))
        demo_3_btn.setStyleSheet('QPushButton { background-color: #2196F3; color: white; padding: 8px; }')
        demo_layout.addWidget(demo_3_btn)
        
        demo_group.setLayout(demo_layout)
        layout.addWidget(demo_group)
        
        return widget
    
    def create_team_numbers_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info_label = QLabel('Team Number Assignments')
        info_font = QFont()
        info_font.setPointSize(12)
        info_font.setBold(True)
        info_label.setFont(info_font)
        layout.addWidget(info_label)
        
        description = QLabel('Each team is assigned a unique number for easy identification during play.')
        description.setWordWrap(True)
        layout.addWidget(description)
        
        self.team_numbers_table = QTableWidget()
        self.team_numbers_table.setColumnCount(3)
        self.team_numbers_table.setHorizontalHeaderLabels(['Number', 'Team Name', 'Players'])
        self.team_numbers_table.horizontalHeader().setStretchLastSection(True)
        self.team_numbers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.team_numbers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.team_numbers_table)
        
        self.update_team_numbers_table()
        
        return widget
    
    def create_rounds_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        btn_layout = QHBoxLayout()
        
        generate_btn = QPushButton('Generate New Round')
        generate_btn.clicked.connect(self.generate_round)
        generate_btn.setStyleSheet('QPushButton { background-color: #4CAF50; color: white; padding: 12px; font-size: 14pt; }')
        btn_layout.addWidget(generate_btn)
        
        big_screen_btn = QPushButton('📺 Big Screen Display')
        big_screen_btn.clicked.connect(self.open_big_screen)
        big_screen_btn.setStyleSheet('QPushButton { font-size: 14pt; padding: 12px; background-color: #2196F3; color: white; }')
        btn_layout.addWidget(big_screen_btn)
        
        sim_btn = QPushButton('🎲 Sim Scores')
        sim_btn.clicked.connect(self.simulate_scores)
        sim_btn.setStyleSheet('QPushButton { font-size: 14pt; padding: 12px; background-color: #9C27B0; color: white; }')
        btn_layout.addWidget(sim_btn)
        
        layout.addLayout(btn_layout)
        
        self.rounds_display = QTextEdit()
        self.rounds_display.setReadOnly(True)
        layout.addWidget(self.rounds_display)
        
        self.update_rounds_display()
        
        return widget
    
    def create_scores_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info_label = QLabel('Click on a game to enter scores')
        info_label.setStyleSheet('font-size: 12pt; font-weight: bold;')
        layout.addWidget(info_label)
        
        self.scores_table = QTableWidget()
        self.scores_table.setColumnCount(6)
        self.scores_table.setHorizontalHeaderLabels(['Round', 'Court', 'Team 1', 'Team 2', 'Score', 'Status'])
        self.scores_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.scores_table.cellDoubleClicked.connect(self.enter_score)
        layout.addWidget(self.scores_table)
        
        self.update_scores_table()
        
        return widget
    
    def create_rankings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        refresh_btn = QPushButton('Refresh Rankings')
        refresh_btn.clicked.connect(self.update_rankings)
        refresh_btn.setStyleSheet('QPushButton { background-color: #2196F3; color: white; padding: 8px; }')
        layout.addWidget(refresh_btn)
        
        self.rankings_table = QTableWidget()
        self.rankings_table.setColumnCount(8)
        self.rankings_table.setHorizontalHeaderLabels(['Rank', 'Team', 'Players', 'Wins', 'Losses', 'Win %', 'Points +/-', 'Games'])
        self.rankings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.rankings_table)
        
        self.update_rankings()
        
        return widget
    
    def create_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info_label = QLabel('Session History')
        info_label.setStyleSheet('font-size: 14pt; font-weight: bold;')
        layout.addWidget(info_label)
        
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.show_history_details)
        layout.addWidget(self.history_list)
        
        self.history_details = QTextEdit()
        self.history_details.setReadOnly(True)
        layout.addWidget(self.history_details)
        
        buttons_layout = QHBoxLayout()
        
        export_btn = QPushButton('Export Selected Session')
        export_btn.clicked.connect(self.export_session)
        export_btn.setStyleSheet('QPushButton { background-color: #2196F3; color: white; padding: 8px; }')
        buttons_layout.addWidget(export_btn)
        
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
        
        new_session_btn = QPushButton('Start New Session')
        new_session_btn.clicked.connect(self.new_session)
        new_session_btn.setStyleSheet('QPushButton { background-color: #ff9800; color: white; padding: 10px; font-size: 12pt; }')
        layout.addWidget(new_session_btn)
        
        data_group = QGroupBox('League Data Management')
        data_layout = QVBoxLayout()
        
        info_text = QLabel('Save and load league data files to manage multiple leagues or continue across weeks.')
        info_text.setWordWrap(True)
        data_layout.addWidget(info_text)
        
        buttons_layout = QHBoxLayout()
        
        export_btn = QPushButton('Export League Data...')
        export_btn.clicked.connect(self.export_league_data)
        export_btn.setStyleSheet('QPushButton { background-color: #2196F3; color: white; padding: 8px; }')
        buttons_layout.addWidget(export_btn)
        
        import_btn = QPushButton('Import League Data...')
        import_btn.clicked.connect(self.import_league_data)
        import_btn.setStyleSheet('QPushButton { background-color: #4CAF50; color: white; padding: 8px; }')
        buttons_layout.addWidget(import_btn)
        
        data_layout.addLayout(buttons_layout)
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        clear_group = QGroupBox('Clear/Delete Data')
        clear_layout = QVBoxLayout()
        
        warning_text = QLabel('⚠️ Use these options carefully - deleted data cannot be recovered!')
        warning_text.setWordWrap(True)
        warning_text.setStyleSheet('color: #ff5722; font-weight: bold;')
        clear_layout.addWidget(warning_text)
        
        clear_buttons_layout = QVBoxLayout()
        
        clear_session_btn = QPushButton('Clear Current Session (Keep History)')
        clear_session_btn.clicked.connect(self.clear_current_session)
        clear_session_btn.setStyleSheet('QPushButton { background-color: #FF9800; color: white; padding: 6px; }')
        clear_buttons_layout.addWidget(clear_session_btn)
        
        clear_history_btn = QPushButton('Clear Session History')
        clear_history_btn.clicked.connect(self.clear_session_history)
        clear_history_btn.setStyleSheet('QPushButton { background-color: #FF5722; color: white; padding: 6px; }')
        clear_buttons_layout.addWidget(clear_history_btn)
        
        reset_all_btn = QPushButton('Reset All Data (Keep Teams)')
        reset_all_btn.clicked.connect(self.reset_all_data)
        reset_all_btn.setStyleSheet('QPushButton { background-color: #E91E63; color: white; padding: 6px; }')
        clear_buttons_layout.addWidget(reset_all_btn)
        
        clear_all_btn = QPushButton('Clear Everything (Including Teams)')
        clear_all_btn.clicked.connect(self.clear_everything)
        clear_all_btn.setStyleSheet('QPushButton { background-color: #D32F2F; color: white; padding: 6px; font-weight: bold; }')
        clear_buttons_layout.addWidget(clear_all_btn)
        
        clear_layout.addLayout(clear_buttons_layout)
        clear_group.setLayout(clear_layout)
        layout.addWidget(clear_group)
        
        layout.addStretch()
        
        self.update_session_info()
        
        return widget
    
    def add_team(self):
        player1 = self.player1_input.text().strip()
        player2 = self.player2_input.text().strip()
        
        if not player1 or not player2:
            QMessageBox.warning(self, 'Error', 'Please enter both player names')
            return
        
        if self.league.add_team(player1, player2):
            self.player1_input.clear()
            self.player2_input.clear()
            self.player1_input.setFocus()
            self.update_teams_list()
            self.update_team_numbers_table()
            self.save_data()
            self.status_label.setText(f'Added team: {player1} & {player2}')
        else:
            QMessageBox.warning(self, 'Error', 'This team pairing already exists')
    
    def remove_team(self):
        current_item = self.teams_list.currentItem()
        if current_item:
            # Extract team name from "#X - Team Name - Players" format
            parts = current_item.text().split(' - ')
            team_name = parts[1] if len(parts) > 1 else parts[0]
            if self.league.remove_team(team_name):
                self.update_teams_list()
                self.update_team_numbers_table()
                self.save_data()
                self.status_label.setText(f'Removed team: {team_name}')
    
    def update_teams_list(self):
        self.teams_list.clear()
        for team in sorted(self.league.teams, key=lambda t: t['name']):
            team_num = self.league.team_numbers.get(team['name'], '?')
            item_text = f"#{team_num} - {team['name']} - {team['player1']} & {team['player2']}"
            self.teams_list.addItem(item_text)
        
        num_courts = self.league.get_active_courts()
        self.status_label.setText(f'Total teams: {len(self.league.teams)} | Active courts: {num_courts}')
    
    def update_team_numbers_table(self):
        # Sort teams by their assigned number
        sorted_teams = sorted(self.league.teams, key=lambda t: self.league.team_numbers.get(t['name'], 999))
        
        self.team_numbers_table.setRowCount(len(sorted_teams))
        
        for i, team in enumerate(sorted_teams):
            team_num = self.league.team_numbers.get(team['name'], '?')
            
            num_item = QTableWidgetItem(f"#{team_num}")
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_font = QFont()
            num_font.setBold(True)
            num_font.setPointSize(11)
            num_item.setFont(num_font)
            self.team_numbers_table.setItem(i, 0, num_item)
            
            name_item = QTableWidgetItem(team['name'])
            self.team_numbers_table.setItem(i, 1, name_item)
            
            players_item = QTableWidgetItem(f"{team['player1']} & {team['player2']}")
            self.team_numbers_table.setItem(i, 2, players_item)
    
    def open_big_screen(self):
        if not self.league.session_rounds:
            QMessageBox.warning(self, 'No Rounds', 'Please generate a round first before opening the big screen display.')
            return
        
        self.big_screen = BigScreenDisplay(self.league, self)
        self.big_screen.show()
    
    def load_demo_teams(self, count=8):
        demo_players = [
            ('Alice', 'Bob'),
            ('Carol', 'Dave'),
            ('Eve', 'Frank'),
            ('Grace', 'Henry'),
            ('Ivy', 'Jack'),
            ('Kate', 'Leo'),
            ('Mia', 'Noah'),
            ('Olivia', 'Paul'),
            ('Quinn', 'Ryan'),
            ('Sam', 'Taylor'),
            ('Uma', 'Victor'),
            ('Wendy', 'Xavier')
        ]
        
        teams_to_add = demo_players[:count]
        added_count = 0
        for player1, player2 in teams_to_add:
            if self.league.add_team(player1, player2):
                added_count += 1
        
        self.update_teams_list()
        self.update_team_numbers_table()
        self.save_data()
        self.status_label.setText(f'Demo mode: Added {added_count} teams')
    
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
        import random
        
        if not self.league.session_rounds:
            QMessageBox.warning(self, 'No Rounds', 'No rounds to simulate scores for.')
            return
            
        count = 0
        for round_idx, round_data in enumerate(self.league.session_rounds, 1):
            for court in round_data['courts']:
                if not court.get('completed', False):
                    # Generate random realistic scores
                    if random.random() > 0.5:
                        s1, s2 = 11, random.randint(0, 9)
                    else:
                        s1, s2 = random.randint(0, 9), 11
                    
                    self.league.record_game_score(round_idx, court['court'], s1, s2)
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
        if not self.league.session_rounds:
            self.rounds_display.setText('No rounds generated yet.\n\nClick "Generate New Round" to start!')
            return
        
        text = f"SESSION #{self.league.current_session}\n"
        text += "=" * 70 + "\n\n"
        
        for round_data in self.league.session_rounds:
            text += f"ROUND {round_data['round_number']}\n"
            text += "-" * 40 + "\n"
            
            for court in round_data['courts']:
                team1 = court['team1']
                team2 = court['team2']
                text += f"Court {court['court']}:\n"
                text += f"  {team1['name']} ({team1['player1']} & {team1['player2']})\n"
                text += f"    vs\n"
                text += f"  {team2['name']} ({team2['player1']} & {team2['player2']})\n"
                
                if court['completed']:
                    text += f"  Final Score: {court['team1_score']} - {court['team2_score']}\n"
                text += "\n"
            
            if round_data['sitting_teams']:
                text += f"Sitting out: {', '.join(round_data['sitting_teams'])}\n"
            text += "\n"
        
        self.rounds_display.setText(text)
    
    def update_scores_table(self):
        self.scores_table.setRowCount(0)
        
        for round_data in self.league.session_rounds:
            for court in round_data['courts']:
                row = self.scores_table.rowCount()
                self.scores_table.insertRow(row)
                
                self.scores_table.setItem(row, 0, QTableWidgetItem(str(round_data['round_number'])))
                self.scores_table.setItem(row, 1, QTableWidgetItem(str(court['court'])))
                
                team1_text = f"{court['team1']['name']}"
                team2_text = f"{court['team2']['name']}"
                self.scores_table.setItem(row, 2, QTableWidgetItem(team1_text))
                self.scores_table.setItem(row, 3, QTableWidgetItem(team2_text))
                
                if court['completed']:
                    score_text = f"{court['team1_score']} - {court['team2_score']}"
                    status_text = "Complete"
                else:
                    score_text = "-"
                    status_text = "Pending"
                
                self.scores_table.setItem(row, 4, QTableWidgetItem(score_text))
                self.scores_table.setItem(row, 5, QTableWidgetItem(status_text))
    
    def enter_score(self, row, col):
        round_num = int(self.scores_table.item(row, 0).text())
        court_num = int(self.scores_table.item(row, 1).text())
        
        round_data = self.league.session_rounds[round_num - 1]
        court = None
        for c in round_data['courts']:
            if c['court'] == court_num:
                court = c
                break
        
        if court and not court['completed']:
            dialog = ScoreDialog(round_num, court_num, court['team1'], court['team2'], self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                team1_score, team2_score = dialog.get_scores()
                if self.league.record_game_score(round_num, court_num, team1_score, team2_score):
                    self.update_scores_table()
                    self.update_rounds_display()
                    self.update_rankings()
                    self.save_data()
                    self.status_label.setText(f'Score recorded: Round {round_num}, Court {court_num}')
    
    def update_rankings(self):
        rankings = self.league.get_rankings()
        
        self.rankings_table.setRowCount(len(rankings))
        
        for i, rank in enumerate(rankings):
            self.rankings_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.rankings_table.setItem(i, 1, QTableWidgetItem(rank['team']))
            self.rankings_table.setItem(i, 2, QTableWidgetItem(f"{rank['player1']} & {rank['player2']}"))
            self.rankings_table.setItem(i, 3, QTableWidgetItem(str(rank['wins'])))
            self.rankings_table.setItem(i, 4, QTableWidgetItem(str(rank['losses'])))
            self.rankings_table.setItem(i, 5, QTableWidgetItem(f"{rank['win_pct']:.1f}%"))
            
            diff_item = QTableWidgetItem(f"{rank['differential']:+d}")
            diff = rank['differential']
            if diff > 0:
                diff_item.setForeground(QColor('green'))
            elif diff < 0:
                diff_item.setForeground(QColor('red'))
            self.rankings_table.setItem(i, 6, diff_item)
            
            self.rankings_table.setItem(i, 7, QTableWidgetItem(str(rank['games_played'])))
    
    def update_session_info(self):
        info = f'Session #{self.league.current_session}\n'
        info += f'Total Rounds: {len(self.league.session_rounds)}\n'
        info += f'Teams: {len(self.league.teams)}\n'
        info += f'Active Courts: {self.league.get_active_courts()}\n\n'
        
        if self.league.teams:
            games_counts = [self.league.team_stats[t['name']]['games_played'] for t in self.league.teams]
            if games_counts:
                min_games = min(games_counts)
                max_games = max(games_counts)
                info += f'Games played: {min_games} to {max_games}\n'
        
        self.session_info.setText(info)
    
    def update_history_list(self):
        self.history_list.clear()
        for session in reversed(self.league.session_history):
            item_text = f"Session #{session['session_number']} - {session['date']} ({session['team_count']} teams)"
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
        details += f"Date: {session['date']}\n"
        details += f"Teams: {session['team_count']}\n"
        details += f"Rounds: {len(session['rounds'])}\n\n"
        details += "=" * 60 + "\n"
        details += "FINAL RANKINGS\n"
        details += "=" * 60 + "\n\n"
        
        for i, rank in enumerate(session['rankings'], 1):
            details += f"{i}. {rank['team']}\n"
            details += f"   Players: {rank['player1']} & {rank['player2']}\n"
            details += f"   Record: {rank['wins']}-{rank['losses']} ({rank['win_pct']:.1f}%)\n"
            details += f"   Point Differential: {rank['differential']:+d}\n"
            details += f"   Games Played: {rank['games_played']}\n\n"
        
        self.history_details.setText(details)
    
    def export_session(self):
        current_item = self.history_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'No Selection', 'Please select a session to export')
            return
        
        session_num = int(current_item.text().split('#')[1].split(' ')[0])
        session = None
        for s in self.league.session_history:
            if s['session_number'] == session_num:
                session = s
                break
        
        if not session:
            return
        
        filename = f"mixed_doubles_session_{session['session_number']}_{session['date'].replace(':', '-').replace(' ', '_')}.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write("=" * 70 + "\n")
                f.write(f"ROC CITY PICKLEBALL - MIXED DOUBLES SESSION #{session['session_number']}\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"Date: {session['date']}\n")
                f.write(f"Teams: {session['team_count']}\n")
                f.write(f"Rounds: {len(session['rounds'])}\n\n")
                
                f.write("=" * 70 + "\n")
                f.write("FINAL RANKINGS\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"{'Rank':<6} {'Team':<20} {'Players':<30} {'W-L':<8} {'Diff':<8}\n")
                f.write("-" * 70 + "\n")
                
                for i, rank in enumerate(session['rankings'], 1):
                    players = f"{rank['player1']} & {rank['player2']}"
                    record = f"{rank['wins']}-{rank['losses']}"
                    diff_str = f"{rank['differential']:+d}"
                    f.write(f"{i:<6} {rank['team']:<20} {players:<30} {record:<8} {diff_str:<8}\n")
                
                f.write("\n\n")
                f.write("=" * 70 + "\n")
                f.write("ROUND DETAILS\n")
                f.write("=" * 70 + "\n\n")
                
                for round_data in session['rounds']:
                    f.write(f"\nROUND {round_data['round_number']}\n")
                    f.write("-" * 40 + "\n")
                    for court in round_data['courts']:
                        team1 = court['team1']
                        team2 = court['team2']
                        f.write(f"Court {court['court']}:\n")
                        f.write(f"  {team1['name']} ({team1['player1']} & {team1['player2']})\n")
                        f.write(f"    vs\n")
                        f.write(f"  {team2['name']} ({team2['player1']} & {team2['player2']})\n")
                        if court['completed']:
                            f.write(f"  Score: {court['team1_score']} - {court['team2_score']}\n")
                        f.write("\n")
                    
                    if round_data['sitting_teams']:
                        f.write(f"Sitting out: {', '.join(round_data['sitting_teams'])}\n")
                    f.write("\n")
            
            QMessageBox.information(self, 'Export Successful', 
                                  f'Session exported to:\n{filename}')
            self.status_label.setText(f'Exported: {filename}')
        except Exception as e:
            QMessageBox.critical(self, 'Export Failed', f'Error: {str(e)}')
    
    def new_session(self):
        reply = QMessageBox.question(self, 'Start New Session', 
                                     'This will save current session to history and start fresh.\n'
                                     'Current rounds and scores will be preserved in History tab.\n\n'
                                     'Are you sure?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.league.new_session()
            self.update_rounds_display()
            self.update_scores_table()
            self.update_rankings()
            self.update_session_info()
            self.update_history_list()
            self.save_data()
            self.status_label.setText('New session started - previous session saved to history')
    
    def export_league_data(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            'Export League Data',
            f'mixed_doubles_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
            'JSON Files (*.json);;All Files (*)'
        )
        
        if filename:
            try:
                self.league.save_to_file(filename)
                QMessageBox.information(self, 'Export Successful', 
                                      f'League data exported to:\n{filename}')
                self.status_label.setText(f'Exported league data to: {filename}')
            except Exception as e:
                QMessageBox.critical(self, 'Export Failed', f'Error exporting data:\n{str(e)}')
    
    def import_league_data(self):
        reply = QMessageBox.question(
            self, 
            'Import League Data', 
            'Importing will replace all current league data.\n'
            'Make sure you have exported your current data if needed.\n\n'
            'Continue with import?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                'Import League Data',
                '',
                'JSON Files (*.json);;All Files (*)'
            )
            
            if filename:
                try:
                    if self.league.load_from_file(filename):
                        self.update_teams_list()
                        self.update_rounds_display()
                        self.update_scores_table()
                        self.update_rankings()
                        self.update_session_info()
                        self.update_history_list()
                        self.save_data()
                        QMessageBox.information(self, 'Import Successful', 
                                              f'League data imported from:\n{filename}')
                        self.status_label.setText(f'Imported league data from: {filename}')
                    else:
                        QMessageBox.critical(self, 'Import Failed', 
                                           'Could not load data from file.\n'
                                           'File may be corrupted or in wrong format.')
                except Exception as e:
                    QMessageBox.critical(self, 'Import Failed', f'Error importing data:\n{str(e)}')
    
    def clear_current_session(self):
        reply = QMessageBox.question(
            self,
            'Clear Current Session',
            'This will delete all rounds and scores from the current session.\n'
            'Session history will be preserved.\n\n'
            'Are you sure?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.league.clear_current_session()
            self.update_rounds_display()
            self.update_scores_table()
            self.update_rankings()
            self.update_session_info()
            self.save_data()
            QMessageBox.information(self, 'Session Cleared', 'Current session has been cleared.')
            self.status_label.setText('Current session cleared')
    
    def clear_session_history(self):
        reply = QMessageBox.question(
            self,
            'Clear Session History',
            'This will permanently delete all session history.\n'
            'Current session will be preserved.\n\n'
            'Are you sure?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.league.clear_history()
            self.update_history_list()
            self.save_data()
            QMessageBox.information(self, 'History Cleared', 'Session history has been cleared.')
            self.status_label.setText('Session history cleared')
    
    def reset_all_data(self):
        reply = QMessageBox.question(
            self,
            'Reset All Data',
            'This will delete:\n'
            '• All rounds and scores\n'
            '• All session history\n'
            '• All team statistics\n\n'
            'Team list will be preserved.\n\n'
            'Are you sure?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.league.reset_all()
            self.update_rounds_display()
            self.update_scores_table()
            self.update_rankings()
            self.update_session_info()
            self.update_history_list()
            self.save_data()
            QMessageBox.information(self, 'Data Reset', 'All data has been reset. Teams preserved.')
            self.status_label.setText('All data reset - teams preserved')
    
    def clear_everything(self):
        reply = QMessageBox.warning(
            self,
            'Clear Everything',
            'WARNING: This will delete EVERYTHING:\n'
            '• All teams\n'
            '• All rounds and scores\n'
            '• All session history\n'
            '• All statistics\n\n'
            'This action cannot be undone!\n\n'
            'Are you absolutely sure?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            confirm = QMessageBox.warning(
                self,
                'Final Confirmation',
                'This is your last chance!\n\n'
                'Delete ALL data including teams?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.Yes:
                self.league.clear_all_data()
                self.update_teams_list()
                self.update_rounds_display()
                self.update_scores_table()
                self.update_rankings()
                self.update_session_info()
                self.update_history_list()
                self.save_data()
                QMessageBox.information(self, 'Everything Cleared', 'All data has been deleted.')
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
