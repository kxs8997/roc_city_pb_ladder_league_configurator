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


class RoundRobinLeague:
    def __init__(self):
        self.players = []
        self.session_rounds = []
        self.current_session = 1
        self.player_stats = {}
        self.session_history = []
        self.player_numbers = {}  # Map player name to assigned number
        self.next_player_number = 1  # Track next available number
        
    def add_player(self, name):
        if name and name not in self.players:
            self.players.append(name)
            self.player_stats[name] = {
                'games_played': 0,
                'wins': 0,
                'losses': 0,
                'total_points': 0,
                'total_points_against': 0,
                'rounds_sat_out': 0,
                'last_sat_out_round': -2,
                'game_scores': []
            }
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
            if name in self.player_numbers:
                del self.player_numbers[name]
            return True
        return False
    
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
    
    def get_players_per_round(self):
        """Calculate how many players play each round"""
        return self.get_active_courts() * 4
    
    def can_sit_out(self, player, current_round_num):
        """Check if player can sit out this round (didn't sit out last round)"""
        last_sat = self.player_stats[player]['last_sat_out_round']
        return (current_round_num - last_sat) > 1
    
    def get_games_played(self, player):
        """Get number of games played by player"""
        return self.player_stats[player]['games_played']
    
    def select_sitting_players(self, current_round_num):
        """Select players to sit out, prioritizing those who haven't sat recently and have more games"""
        num_courts = self.get_active_courts()
        players_per_round = num_courts * 4
        num_sitting = len(self.players) - players_per_round
        
        if num_sitting <= 0:
            return []
        
        # Score each player for sitting priority
        sit_scores = []
        for player in self.players:
            if not self.can_sit_out(player, current_round_num):
                continue
            
            games_played = self.get_games_played(player)
            rounds_sat = self.player_stats[player]['rounds_sat_out']
            last_sat = self.player_stats[player]['last_sat_out_round']
            
            # Higher score = more likely to sit
            score = games_played * 10 - rounds_sat * 20 + (current_round_num - last_sat)
            sit_scores.append((player, score))
        
        # Sort by score (highest first) and select top num_sitting
        sit_scores.sort(key=lambda x: x[1], reverse=True)
        sitting_players = [p for p, _ in sit_scores[:num_sitting]]
        
        # If we don't have enough eligible players, force some to sit
        if len(sitting_players) < num_sitting:
            remaining = [p for p in self.players if p not in sitting_players]
            random.shuffle(remaining)
            sitting_players.extend(remaining[:num_sitting - len(sitting_players)])
        
        return sitting_players
    
    def generate_round(self):
        """Generate a new round with proper sit-out rotation"""
        num_courts = self.get_active_courts()
        
        if len(self.players) < num_courts * 4:
            return None, f"Need at least {num_courts * 4} players for {num_courts} courts"
        
        current_round_num = len(self.session_rounds) + 1
        
        # Select who sits out
        sitting_players = self.select_sitting_players(current_round_num)
        
        # Get playing players
        playing_players = [p for p in self.players if p not in sitting_players]
        random.shuffle(playing_players)
        
        # Assign to courts
        courts = []
        for court_num in range(1, num_courts + 1):
            start_idx = (court_num - 1) * 4
            court_players = playing_players[start_idx:start_idx + 4]
            
            if len(court_players) == 4:
                courts.append({
                    'court': court_num,
                    'players': court_players,
                    'team1': court_players[:2],
                    'team2': court_players[2:],
                    'team1_score': 0,
                    'team2_score': 0,
                    'completed': False
                })
        
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
        
        # Update player stats
        team1_won = team1_score > team2_score
        for player in court['team1']:
            self.player_stats[player]['games_played'] += 1
            self.player_stats[player]['wins'] += 1 if team1_won else 0
            self.player_stats[player]['losses'] += 0 if team1_won else 1
            self.player_stats[player]['total_points'] += team1_score
            self.player_stats[player]['total_points_against'] += team2_score
            self.player_stats[player]['game_scores'].append({
                'round': round_num,
                'points_for': team1_score,
                'points_against': team2_score
            })
        
        for player in court['team2']:
            self.player_stats[player]['games_played'] += 1
            self.player_stats[player]['wins'] += 0 if team1_won else 1
            self.player_stats[player]['losses'] += 1 if team1_won else 0
            self.player_stats[player]['total_points'] += team2_score
            self.player_stats[player]['total_points_against'] += team1_score
            self.player_stats[player]['game_scores'].append({
                'round': round_num,
                'points_for': team2_score,
                'points_against': team1_score
            })
        
        return True
    
    def get_rankings(self):
        """Get player rankings based on wins, then differential"""
        if not self.players:
            return []
        
        rankings = []
        for player in self.players:
            stats = self.player_stats[player]
            games_played = stats['games_played']
            wins = stats.get('wins', 0)
            losses = stats.get('losses', 0)
            points = stats['total_points']
            points_against = stats['total_points_against']
            differential = points - points_against
            
            rankings.append({
                'player': player,
                'games_played': games_played,
                'wins': wins,
                'losses': losses,
                'points': points,
                'points_against': points_against,
                'differential': differential
            })
        
        # Sort by wins (desc), then differential (desc), then points (desc)
        rankings.sort(key=lambda x: (x['wins'], x['differential'], x['points']), reverse=True)
        
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
                'player_count': len(self.players)
            }
            self.session_history.append(session_data)
        
        # Clear current session rounds but KEEP cumulative stats (no ladder/tiers)
        self.session_rounds = []
        # Only reset sit-out tracking for new session, keep points cumulative
        for player in self.players:
            self.player_stats[player]['rounds_sat_out'] = 0
            self.player_stats[player]['last_sat_out_round'] = -2
        self.current_session += 1
    
    def clear_current_session(self):
        """Clear current session rounds and scores without saving to history"""
        self.session_rounds = []
        for player in self.players:
            self.player_stats[player] = {
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
        """Reset everything except players"""
        self.session_rounds = []
        self.current_session = 1
        self.session_history = []
        for player in self.players:
            self.player_stats[player] = {
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
        """Clear everything including players"""
        self.players = []
        self.session_rounds = []
        self.current_session = 1
        self.player_stats = {}
        self.session_history = []
        self.player_numbers = {}
        self.next_player_number = 1
    
    def save_to_file(self, filename):
        data = {
            'players': self.players,
            'session_rounds': self.session_rounds,
            'current_session': self.current_session,
            'player_stats': self.player_stats,
            'session_history': self.session_history,
            'player_numbers': self.player_numbers,
            'next_player_number': self.next_player_number
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
                self.player_numbers = data.get('player_numbers', {})
                self.next_player_number = data.get('next_player_number', 1)
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
        
        # Round number
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
        self.league = RoundRobinLeague()
        self.data_file = Path('round_robin_data.json')
        
        if self.data_file.exists():
            self.league.load_from_file(self.data_file)
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('ROC City Pickleball - Round Robin League Manager')
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
        
        title_label = QLabel('Round Robin League Manager')
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        self.status_label = QLabel('Ready')
        main_layout.addWidget(self.status_label)
        
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        tabs.addTab(self.create_players_tab(), 'Players')
        tabs.addTab(self.create_player_numbers_tab(), 'Player Numbers')
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
        
        demo_btn = QPushButton('Load Demo Players (16)')
        demo_btn.clicked.connect(self.load_demo_players)
        demo_btn.setStyleSheet('QPushButton { background-color: #4CAF50; color: white; padding: 8px; }')
        buttons_layout.addWidget(demo_btn)
        
        demo_btn_24 = QPushButton('Load Demo Players (24)')
        demo_btn_24.clicked.connect(lambda: self.load_demo_players(24))
        demo_btn_24.setStyleSheet('QPushButton { background-color: #4CAF50; color: white; padding: 8px; }')
        buttons_layout.addWidget(demo_btn_24)
        
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
        self.player_numbers_table.setColumnCount(2)
        self.player_numbers_table.setHorizontalHeaderLabels(['Number', 'Player Name'])
        self.player_numbers_table.horizontalHeader().setStretchLastSection(True)
        self.player_numbers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.player_numbers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.player_numbers_table)
        
        self.update_player_numbers_table()
        
        return widget
    
    def create_rounds_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info_label = QLabel('Generate rounds for your session. Players will rotate through courts\n'
                           'and sit-outs to ensure everyone plays minimum 5 games.')
        info_label.setWordWrap(True)
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
        self.scores_player_numbers_table.setColumnCount(2)
        self.scores_player_numbers_table.setHorizontalHeaderLabels(['#', 'Player'])
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
        layout = QVBoxLayout(widget)
        
        info_label = QLabel('Player rankings based on wins, then point differential')
        layout.addWidget(info_label)
        
        self.rankings_table = QTableWidget()
        self.rankings_table.setColumnCount(7)
        self.rankings_table.setHorizontalHeaderLabels(['Rank', 'Player', 'W', 'L', 'Games', 'Points', 'Diff'])
        layout.addWidget(self.rankings_table)
        
        refresh_btn = QPushButton('Refresh Rankings')
        refresh_btn.clicked.connect(self.update_rankings)
        layout.addWidget(refresh_btn)
        
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
        
        reset_all_btn = QPushButton('Reset All Data (Keep Players)')
        reset_all_btn.clicked.connect(self.reset_all_data)
        reset_all_btn.setStyleSheet('QPushButton { background-color: #E91E63; color: white; padding: 6px; }')
        clear_buttons_layout.addWidget(reset_all_btn)
        
        clear_all_btn = QPushButton('Clear Everything (Including Players)')
        clear_all_btn.clicked.connect(self.clear_everything)
        clear_all_btn.setStyleSheet('QPushButton { background-color: #D32F2F; color: white; padding: 6px; font-weight: bold; }')
        clear_buttons_layout.addWidget(clear_all_btn)
        
        clear_layout.addLayout(clear_buttons_layout)
        clear_group.setLayout(clear_layout)
        layout.addWidget(clear_group)
        
        layout.addStretch()
        
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
            # Extract player name from "#X - Name" format
            name = display_text.split(' - ', 1)[1] if ' - ' in display_text else display_text
            if self.league.remove_player(name):
                self.update_players_list()
                self.update_player_numbers_table()
                self.update_scores_player_numbers()
                self.save_data()
                self.status_label.setText(f'Removed player: {name}')
    
    def update_players_list(self):
        self.players_list.clear()
        for player in sorted(self.league.players):
            player_num = self.league.player_numbers.get(player, '?')
            self.players_list.addItem(f"#{player_num} - {player}")
        
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
    
    def load_demo_players(self, count=16):
        all_demo_players = [
            "Alex Martinez", "Blake Johnson", "Casey Williams", "Drew Anderson",
            "Emma Thompson", "Frank Garcia", "Grace Miller", "Henry Davis",
            "Iris Rodriguez", "Jack Wilson", "Kelly Moore", "Logan Taylor",
            "Maya Jackson", "Noah White", "Olivia Harris", "Parker Martin",
            "Quinn Roberts", "Riley Cooper", "Sam Peterson", "Taylor Brooks",
            "Uma Patel", "Victor Chen", "Willow Singh", "Xavier Lee"
        ]
        
        demo_players = all_demo_players[:count]
        
        reply = QMessageBox.question(self, 'Load Demo Players', 
                                     f'This will add {count} sample players for testing.\n'
                                     'Current players will be kept.\n\nContinue?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            added_count = 0
            for player in demo_players:
                if self.league.add_player(player):
                    added_count += 1
            
            self.update_players_list()
            self.update_player_numbers_table()
            self.update_scores_player_numbers()
            self.save_data()
            self.status_label.setText(f'Demo mode: Added {added_count} players')
    
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
            if self.league.record_game_score(round_num, court_num, team1_score, team2_score):
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
            # Add player number to rankings
            player_num = self.league.player_numbers.get(rank_data['player'], '?')
            self.rankings_table.setItem(i, 1, QTableWidgetItem(f"#{player_num} {rank_data['player']}"))
            self.rankings_table.setItem(i, 2, QTableWidgetItem(str(rank_data.get('wins', 0))))
            self.rankings_table.setItem(i, 3, QTableWidgetItem(str(rank_data.get('losses', 0))))
            self.rankings_table.setItem(i, 4, QTableWidgetItem(str(rank_data['games_played'])))
            self.rankings_table.setItem(i, 5, QTableWidgetItem(str(rank_data['points'])))
            
            diff = rank_data['differential']
            diff_text = f"+{diff}" if diff > 0 else str(diff)
            diff_item = QTableWidgetItem(diff_text)
            if diff > 0:
                diff_item.setForeground(QColor('green'))
            elif diff < 0:
                diff_item.setForeground(QColor('red'))
            self.rankings_table.setItem(i, 6, diff_item)
    
    def update_session_info(self):
        info = f'Session #{self.league.current_session}\n'
        info += f'Total Rounds: {len(self.league.session_rounds)}\n'
        info += f'Players: {len(self.league.players)}\n'
        info += f'Active Courts: {self.league.get_active_courts()}\n\n'
        
        if self.league.players:
            min_games = min(self.league.player_stats[p]['games_played'] for p in self.league.players)
            max_games = max(self.league.player_stats[p]['games_played'] for p in self.league.players)
            info += f'Games played: {min_games} to {max_games}\n'
        
        self.session_info.setText(info)
    
    def update_history_list(self):
        self.history_list.clear()
        for session in reversed(self.league.session_history):
            item_text = f"Session #{session['session_number']} - {session['date']} ({session['player_count']} players)"
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
        details += f"Players: {session['player_count']}\n"
        details += f"Rounds: {len(session['rounds'])}\n\n"
        details += "=" * 60 + "\n"
        details += "FINAL RANKINGS\n"
        details += "=" * 60 + "\n\n"
        
        for i, rank in enumerate(session['rankings'], 1):
            details += f"{i}. {rank['player']}\n"
            details += f"   Points: {rank['points']} (from {rank['counted_games']} games)\n"
            details += f"   Differential: {rank['differential']:+d}\n"
            details += f"   Total Games: {rank['games_played']}\n\n"
        
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
        
        filename = f"session_{session['session_number']}_{session['date'].replace(':', '-').replace(' ', '_')}.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write("=" * 70 + "\n")
                f.write(f"ROC CITY PICKLEBALL - SESSION #{session['session_number']}\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"Date: {session['date']}\n")
                f.write(f"Players: {session['player_count']}\n")
                f.write(f"Rounds: {len(session['rounds'])}\n\n")
                
                f.write("=" * 70 + "\n")
                f.write("FINAL RANKINGS\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"{'Rank':<6} {'Player':<25} {'Points':<8} {'Diff':<8} {'Games':<6}\n")
                f.write("-" * 70 + "\n")
                
                for i, rank in enumerate(session['rankings'], 1):
                    diff_str = f"{rank['differential']:+d}"
                    f.write(f"{i:<6} {rank['player']:<25} {rank['points']:<8} {diff_str:<8} {rank['games_played']:<6}\n")
                
                f.write("\n\n")
                f.write("=" * 70 + "\n")
                f.write("ROUND DETAILS\n")
                f.write("=" * 70 + "\n\n")
                
                for round_data in session['rounds']:
                    f.write(f"\nROUND {round_data['round_number']}\n")
                    f.write("-" * 40 + "\n")
                    for court in round_data['courts']:
                        f.write(f"Court {court['court']}:\n")
                        f.write(f"  Team 1: {court['team1'][0]} & {court['team1'][1]}\n")
                        f.write(f"  Team 2: {court['team2'][0]} & {court['team2'][1]}\n")
                        if court['completed']:
                            f.write(f"  Score: {court['team1_score']} - {court['team2_score']}\n")
                        f.write("\n")
                    
                    if round_data['sitting_players']:
                        f.write(f"Sitting out: {', '.join(round_data['sitting_players'])}\n")
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
            f'league_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
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
                        self.update_players_list()
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
            '• All player statistics\n\n'
            'Player list will be preserved.\n\n'
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
            QMessageBox.information(self, 'Data Reset', 'All data has been reset. Players preserved.')
            self.status_label.setText('All data reset - players preserved')
    
    def clear_everything(self):
        reply = QMessageBox.warning(
            self,
            'Clear Everything',
            'WARNING: This will delete EVERYTHING:\n'
            '• All players\n'
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
                'Delete ALL data including players?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.Yes:
                self.league.clear_all_data()
                self.update_players_list()
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
