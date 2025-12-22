import sys
import json
import random
import os
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, 
                             QLineEdit, QSpinBox, QTabWidget, QTextEdit,
                             QMessageBox, QGroupBox, QScrollArea)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class LadderLeague:
    def __init__(self):
        self.players = []
        self.match_history = []
        self.court_history = []
        self.num_courts = 4
        
    def add_player(self, name):
        if name and name not in self.players:
            self.players.append(name)
            return True
        return False
    
    def remove_player(self, name):
        if name in self.players:
            self.players.remove(name)
            return True
        return False
    
    def get_matchup_count(self, player1, player2):
        count = 0
        for match in self.match_history:
            if player1 in match and player2 in match:
                count += 1
        return count
    
    def get_court_count(self, player, court):
        count = 0
        for record in self.court_history:
            if record['player'] == player and record['court'] == court:
                count += 1
        return count
    
    def generate_round(self):
        if len(self.players) < 8:
            return None, "Need at least 8 players (2 per court x 4 courts)"
        
        available_players = self.players.copy()
        random.shuffle(available_players)
        
        courts = []
        attempts = 0
        max_attempts = 1000
        
        while len(courts) < self.num_courts and len(available_players) >= 4 and attempts < max_attempts:
            attempts += 1
            
            if len(available_players) < 4:
                break
                
            court_num = len(courts) + 1
            players_for_court = []
            
            for _ in range(4):
                if not available_players:
                    break
                    
                best_player = None
                best_score = float('inf')
                
                for player in available_players:
                    score = 0
                    
                    for existing_player in players_for_court:
                        score += self.get_matchup_count(player, existing_player) * 10
                    
                    score += self.get_court_count(player, court_num) * 5
                    
                    if score < best_score:
                        best_score = score
                        best_player = player
                
                if best_player:
                    players_for_court.append(best_player)
                    available_players.remove(best_player)
            
            if len(players_for_court) == 4:
                courts.append({
                    'court': court_num,
                    'players': players_for_court
                })
        
        if len(courts) < self.num_courts:
            return None, f"Could only fill {len(courts)} courts. Need more players."
        
        for court in courts:
            for i in range(len(court['players'])):
                for j in range(i + 1, len(court['players'])):
                    self.match_history.append([court['players'][i], court['players'][j]])
            
            for player in court['players']:
                self.court_history.append({
                    'player': player,
                    'court': court['court']
                })
        
        return courts, None
    
    def save_to_file(self, filename):
        data = {
            'players': self.players,
            'match_history': self.match_history,
            'court_history': self.court_history
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filename):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                self.players = data.get('players', [])
                self.match_history = data.get('match_history', [])
                self.court_history = data.get('court_history', [])
            return True
        except:
            return False
    
    def reset_history(self):
        self.match_history = []
        self.court_history = []


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.league = LadderLeague()
        self.data_file = Path('ladder_league_data.json')
        
        if self.data_file.exists():
            self.league.load_from_file(self.data_file)
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('ROC City Pickleball - Ladder League Configurator')
        self.setGeometry(100, 100, 900, 700)
        
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
        
        title_label = QLabel('Ladder League Configurator')
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
        tabs.addTab(self.create_schedule_tab(), 'Schedule Round')
        tabs.addTab(self.create_stats_tab(), 'Statistics')
    
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
        
        demo_btn = QPushButton('Load Demo Players')
        demo_btn.clicked.connect(self.load_demo_players)
        demo_btn.setStyleSheet('QPushButton { background-color: #4CAF50; color: white; padding: 8px; }')
        buttons_layout.addWidget(demo_btn)
        
        reset_btn = QPushButton('Reset Match History')
        reset_btn.clicked.connect(self.reset_history)
        buttons_layout.addWidget(reset_btn)
        
        layout.addLayout(buttons_layout)
        
        return widget
    
    def create_schedule_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info_label = QLabel('Generate a new round of matches across 4 courts.\n'
                           'The algorithm ensures players don\'t repeat courts or opponents too often.')
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        generate_btn = QPushButton('Generate New Round')
        generate_btn.clicked.connect(self.generate_round)
        generate_btn.setStyleSheet('QPushButton { font-size: 14pt; padding: 10px; background-color: #88cc00; }')
        layout.addWidget(generate_btn)
        
        self.schedule_display = QTextEdit()
        self.schedule_display.setReadOnly(True)
        self.schedule_display.setStyleSheet('QTextEdit { font-family: Courier; font-size: 11pt; }')
        layout.addWidget(self.schedule_display)
        
        return widget
    
    def create_stats_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        refresh_btn = QPushButton('Refresh Statistics')
        refresh_btn.clicked.connect(self.update_stats)
        layout.addWidget(refresh_btn)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        scroll.setWidget(self.stats_display)
        layout.addWidget(scroll)
        
        self.update_stats()
        
        return widget
    
    def add_player(self):
        name = self.player_name_input.text().strip()
        if self.league.add_player(name):
            self.player_name_input.clear()
            self.update_players_list()
            self.save_data()
            self.status_label.setText(f'Added player: {name}')
        else:
            QMessageBox.warning(self, 'Error', 'Player name is empty or already exists')
    
    def remove_player(self):
        current_item = self.players_list.currentItem()
        if current_item:
            name = current_item.text()
            if self.league.remove_player(name):
                self.update_players_list()
                self.save_data()
                self.status_label.setText(f'Removed player: {name}')
    
    def update_players_list(self):
        self.players_list.clear()
        for player in sorted(self.league.players):
            self.players_list.addItem(player)
        self.status_label.setText(f'Total players: {len(self.league.players)}')
    
    def generate_round(self):
        courts, error = self.league.generate_round()
        
        if error:
            QMessageBox.warning(self, 'Cannot Generate Round', error)
            return
        
        output = f'=== ROUND GENERATED - {datetime.now().strftime("%Y-%m-%d %H:%M")} ===\n\n'
        
        for court in courts:
            output += f'COURT {court["court"]}:\n'
            output += f'  Team 1: {court["players"][0]} & {court["players"][1]}\n'
            output += f'  Team 2: {court["players"][2]} & {court["players"][3]}\n\n'
        
        sitting_out = [p for p in self.league.players if not any(p in court['players'] for court in courts)]
        if sitting_out:
            output += f'Sitting out: {", ".join(sitting_out)}\n'
        
        self.schedule_display.setText(output)
        self.save_data()
        self.status_label.setText('Round generated successfully!')
    
    def load_demo_players(self):
        reply = QMessageBox.question(self, 'Load Demo Players', 
                                     'This will add 16 sample players for testing.\n'
                                     'Current players will be kept.\n\nContinue?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            demo_players = [
                "Alex Martinez", "Blake Johnson", "Casey Williams", "Drew Anderson",
                "Emma Thompson", "Frank Garcia", "Grace Miller", "Henry Davis",
                "Iris Rodriguez", "Jack Wilson", "Kelly Moore", "Logan Taylor",
                "Maya Jackson", "Noah White", "Olivia Harris", "Parker Martin"
            ]
            
            added_count = 0
            for player in demo_players:
                if self.league.add_player(player):
                    added_count += 1
            
            self.update_players_list()
            self.save_data()
            self.status_label.setText(f'Demo mode: Added {added_count} players')
            
            if added_count > 0:
                QMessageBox.information(self, 'Demo Players Loaded', 
                                      f'Added {added_count} demo players!\n\n'
                                      'You can now:\n'
                                      '1. Go to "Schedule Round" tab\n'
                                      '2. Click "Generate New Round"\n'
                                      '3. View statistics in "Statistics" tab\n\n'
                                      'Generate multiple rounds to see the rotation algorithm in action!')
    
    def reset_history(self):
        reply = QMessageBox.question(self, 'Reset History', 
                                     'Are you sure you want to reset all match and court history?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.league.reset_history()
            self.save_data()
            self.update_stats()
            self.status_label.setText('History reset')
    
    def update_stats(self):
        if not self.league.players:
            self.stats_display.setText('No players added yet.')
            return
        
        stats = '=== PLAYER STATISTICS ===\n\n'
        
        for player in sorted(self.league.players):
            stats += f'{player}:\n'
            
            court_counts = {}
            for i in range(1, 5):
                court_counts[i] = self.league.get_court_count(player, i)
            stats += f'  Courts played: '
            stats += ', '.join([f'Court {i}: {court_counts[i]}' for i in range(1, 5)])
            stats += '\n'
            
            total_matches = sum(1 for record in self.league.court_history if record['player'] == player)
            stats += f'  Total rounds: {total_matches // 4}\n\n'
        
        stats += '\n=== MATCHUP FREQUENCY ===\n\n'
        matchups = {}
        for i, p1 in enumerate(sorted(self.league.players)):
            for p2 in sorted(self.league.players)[i+1:]:
                count = self.league.get_matchup_count(p1, p2)
                if count > 0:
                    matchups[f'{p1} vs {p2}'] = count
        
        if matchups:
            for matchup, count in sorted(matchups.items(), key=lambda x: x[1], reverse=True):
                stats += f'{matchup}: {count} times\n'
        else:
            stats += 'No matches played yet.\n'
        
        self.stats_display.setText(stats)
    
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
