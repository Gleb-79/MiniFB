import base64
import colorsys
from functools import partial
import json
import math
import os
import random
import struct
import tempfile
import wave

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.core.text import Label as CoreLabel
from kivy.graphics import (Canvas, Color, Ellipse, Line, Mesh, PopMatrix, PushMatrix, Quad,
                           Rectangle, RoundedRectangle, Scale, Translate, Triangle)
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.resources import resource_find
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import FadeTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex as hexc, platform

GREEN = "#167a31"
GREEN_LIGHT = "#1f9640"  # светлая полоса газона
BLUE = "#1358b8"

# Шрифт со стрелками (в стандартном Roboto диагональных стрелок может не быть)
ARROW_FONT = resource_find("data/fonts/DejaVuSans.ttf") or "Roboto"

if platform in ("win", "linux", "macosx"):
    Window.size = (480, 700)
    Window.minimum_width, Window.minimum_height = 480, 700


class Settings:
    """Пользовательские настройки: звук игры, музыка заставки, язык интерфейса.
    Хранятся в settings.json в папке данных приложения и подхватываются при следующем запуске.
    """

    FILE_NAME = "settings.json"
    LANGUAGES = (("en", "English"), ("ru", "Русский"))   # (код, название на своём языке)

    def __init__(self):
        self.sound_on = True
        self.music_on = True
        self.lang = "en"
        self.first_move = "you"          # кто ходит первым в новой партии: "you" или "cpu"
        self.path = None

    def load(self, folder):
        self.path = os.path.join(folder, self.FILE_NAME) if folder else None
        if not self.path:
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        self.sound_on = bool(data.get("sound", True))
        self.music_on = bool(data.get("music", True))
        if data.get("lang") in dict(self.LANGUAGES):
            self.lang = data["lang"]
        if data.get("first") in ("you", "cpu"):
            self.first_move = data["first"]

    def save(self):
        if not self.path:
            return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"sound": self.sound_on, "music": self.music_on,
                           "lang": self.lang, "first": self.first_move}, f, ensure_ascii=False)
        except OSError:
            pass


SETTINGS = Settings()

I18N = {
    "en": {
        "choose_level": "Choose level",
        "level": "Level:",
        "level_Easy": "Easy",
        "level_Normal": "Normal",
        "level_Hard": "Hard",
        "rules": "RULES",
        "rules_title": "RULES",
        "settings": "SETTINGS",
        "settings_title": "SETTINGS",
        "exit": "EXIT",
        "pause": "Pause",
        "continue": "Continue",
        "paused": "PAUSED",
        "to_menu": "Exit to Main Menu",
        "exit_q": "Exit to the main menu?\nThe current game will be lost.",
        "sound": "Sound effects",
        "music": "Menu music",
        "language": "Language",
        "first_move": "First move",
        "two_players": "2 PLAYERS",
        "player1": "PLAYER 1",
        "player2": "PLAYER 2",
        "p1_move": "Player 1's move",
        "p2_move": "Player 2's move",
        "goal_p1": "GOAL! PLAYER 1 WINS!",
        "goal_p2": "GOAL! PLAYER 2 WINS!",
        "close": "Close",
        "you": "YOU",
        "cpu": "CPU",
        "your_move": "It's your move",
        "not_your_move": "It's not your move",
        "game_over": "GAME OVER",
        "goal_win": "GOAL! YOU WIN!",
        "goal_lose": "GOAL! YOU LOSE!",
        "draw": "DRAW GAME",
        "no_moves": "No valid move",
        "new_game_q": "Start a new game?",
        "yes": "Yes",
        "no": "No",
        "rules_text": (
            "GOAL\n"
            "Bring the ball into the opponent's gate. You attack the top gate, "
            "the CPU attacks the bottom one.\n\n"
            "MOVES\n"
            "Players take turns moving the ball one step in any of 6 directions. "
            "Every line segment can be used only once.\n\n"
            "EXTRA MOVE\n"
            "You move again if the ball lands on a point that was already visited, "
            "bounces off the border of the field, or lands on a horizontal line of the field.\n\n"
            "GATE CENTRE\n"
            "There is no border in the centre of a gate, so the ball doesn't bounce "
            "and the turn passes to the opponent.\n\n"
            "DRAW\n"
            "If the player to move has no legal moves, the game is a draw.\n\n"
            "LEVELS\n"
            "Easy - the CPU prefers moving down and doesn't look ahead.\n"
            "Normal - the CPU thinks 2 moves ahead.\n"
            "Hard - the CPU thinks 6 moves ahead."
        ),
    },
    "ru": {
        "choose_level": "Выберите уровень",
        "level": "Уровень:",
        "level_Easy": "Лёгкий",
        "level_Normal": "Средний",
        "level_Hard": "Сложный",
        "rules": "ПРАВИЛА",
        "rules_title": "ПРАВИЛА",
        "settings": "НАСТРОЙКИ",
        "settings_title": "НАСТРОЙКИ",
        "exit": "ВЫХОД",
        "pause": "Пауза",
        "continue": "Продолжить",
        "paused": "ПАУЗА",
        "to_menu": "В главное меню",
        "exit_q": "Выйти в главное меню?\nТекущая партия будет потеряна.",
        "sound": "Звук в игре",
        "music": "Музыка в меню",
        "language": "Язык",
        "first_move": "Первый ход",
        "two_players": "2 ИГРОКА",
        "player1": "ИГРОК 1",
        "player2": "ИГРОК 2",
        "p1_move": "Ход игрока 1",
        "p2_move": "Ход игрока 2",
        "goal_p1": "ГОЛ! ПОБЕДИЛ ИГРОК 1!",
        "goal_p2": "ГОЛ! ПОБЕДИЛ ИГРОК 2!",
        "close": "Закрыть",
        "you": "ВЫ",
        "cpu": "CPU",
        "your_move": "Ваш ход",
        "not_your_move": "Ход соперника",
        "game_over": "ИГРА ОКОНЧЕНА",
        "goal_win": "ГОЛ! ВЫ ПОБЕДИЛИ!",
        "goal_lose": "ГОЛ! ВЫ ПРОИГРАЛИ!",
        "draw": "НИЧЬЯ",
        "no_moves": "Нет допустимых ходов",
        "new_game_q": "Начать новую игру?",
        "yes": "Да",
        "no": "Нет",
        "rules_text": (
            "ЦЕЛЬ\n"
            "Проведите мяч в ворота соперника. Вы атакуете верхние ворота, "
            "компьютер — нижние.\n\n"
            "ХОДЫ\n"
            "Игроки по очереди передвигают мяч на один шаг в любом из 6 направлений. "
            "Каждый отрезок линии можно использовать только один раз.\n\n"
            "ДОПОЛНИТЕЛЬНЫЙ ХОД\n"
            "Вы ходите ещё раз, если мяч попал в уже посещённую точку, "
            "отскочил от границы поля или попал на горизонтальную линию поля.\n\n"
            "ЦЕНТР ВОРОТ\n"
            "В центре ворот борта нет, поэтому мяч не отскакивает, "
            "и ход переходит к сопернику.\n\n"
            "НИЧЬЯ\n"
            "Если у игрока, чей ход, нет допустимых ходов, игра заканчивается вничью.\n\n"
            "УРОВНИ\n"
            "Лёгкий — компьютер предпочитает ходить вниз и не просчитывает ходы вперёд.\n"
            "Средний — компьютер думает на 2 хода вперёд.\n"
            "Сложный — компьютер думает на 6 ходов вперёд."
        ),
    },
}


def tr(key):
    """Текст интерфейса на выбранном языке (если перевода нет — английский)."""
    table = I18N.get(SETTINGS.lang) or I18N["en"]
    return table.get(key) or I18N["en"][key]


class SoundFX:
    """Звуки хода и гола. Если файлов нет — синтезирует их сам (WAV, без доп. библиотек).

    Свои звуки: положите move.wav/.ogg/.mp3, goal.wav/.ogg/.mp3 и whistle.wav/.ogg/.mp3
    (свисток при ничьей) в папку sounds рядом со скриптом.
    """

    RATE = 22050
    SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")

    def __init__(self, fallback_dir=None):
        self.sounds = {}
        builders = {"move": self._build_move, "goal": self._build_goal,
                    "whistle": self._build_whistle}
        for name, builder in builders.items():
            path = self._find_existing(name)
            if path is None:
                path = self._generate(name, builder, fallback_dir)
            self.sounds[name] = SoundLoader.load(path) if path else None

    def _find_existing(self, name):
        for ext in ("wav", "ogg", "mp3"):
            path = os.path.join(self.SOUND_DIR, f"{name}.{ext}")
            if os.path.exists(path):
                return path
        return None

    def _generate(self, name, builder, fallback_dir):
        data = builder()
        for folder in (self.SOUND_DIR, fallback_dir):
            if not folder:
                continue
            try:
                os.makedirs(folder, exist_ok=True)
                path = os.path.join(folder, f"{name}.wav")
                self._write_wav(path, data)
                return path
            except OSError:
                continue
        return None

    def play(self, name):
        if not SETTINGS.sound_on:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        try:
            sound.stop()      # чтобы быстрые ходы подряд звучали заново
            sound.play()
        except Exception:
            pass

    # ---------- синтез ----------
    def _write_wav(self, path, samples):
        peak = max(abs(v) for v in samples) or 1.0
        gain = 0.8 / peak                      # нормализация, чтобы не было клиппинга
        samples = [v * gain for v in samples]
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.RATE)
            w.writeframes(b"".join(
                struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32000)) for v in samples
            ))

    def _build_move(self):
        """Короткий «удар по мячу»: падающий по частоте тон + щелчок."""
        rng = random.Random(1)
        n = int(0.16 * self.RATE)
        out, phase = [], 0.0
        for i in range(n):
            t = i / self.RATE
            freq = 70 + 190 * math.exp(-t * 22)
            phase += 2 * math.pi * freq / self.RATE
            tone = math.sin(phase) * math.exp(-t * 26)
            click = rng.uniform(-1, 1) * math.exp(-t * 180)
            out.append(0.85 * tone + 0.45 * click)
        return out

    def _build_whistle(self):
        """Только свисток судьи (без трибун) — звук ничьей."""
        total = int(0.9 * self.RATE)
        out = [0.0] * total
        whistle_len = int(0.8 * self.RATE)
        phase = 0.0
        for i in range(whistle_len):
            t = i / self.RATE
            freq = 2700 + 160 * math.sin(2 * math.pi * 26 * t)
            phase += 2 * math.pi * freq / self.RATE
            env = min(1.0, t / 0.02) * min(1.0, (0.8 - t) / 0.08)
            out[i] = env * math.sin(phase) * (0.75 + 0.25 * math.sin(2 * math.pi * 26 * t))
        return out

    def _build_goal(self):
        """Свисток судьи + рёв трибун."""
        rng = random.Random(2)
        total = int(1.7 * self.RATE)
        out = [0.0] * total

        # свисток: тон ~2.7 кГц с быстрым дрожанием (трель)
        whistle_len = int(0.6 * self.RATE)
        phase = 0.0
        for i in range(whistle_len):
            t = i / self.RATE
            freq = 2700 + 160 * math.sin(2 * math.pi * 26 * t)
            phase += 2 * math.pi * freq / self.RATE
            env = min(1.0, t / 0.02) * min(1.0, (0.6 - t) / 0.08)
            out[i] += 0.32 * env * math.sin(phase) * (0.75 + 0.25 * math.sin(2 * math.pi * 26 * t))

        # трибуны: фильтрованный шум с нарастанием и затуханием
        start = int(0.3 * self.RATE)
        slow = fast = 0.0
        for i in range(start, total):
            t = (i - start) / self.RATE
            noise = rng.uniform(-1, 1)
            fast += 0.30 * (noise - fast)
            slow += 0.04 * (noise - slow)
            band = fast - slow
            env = min(1.0, t / 0.25) * math.exp(-max(0.0, t - 0.4) * 2.2)
            out[i] += 1.6 * band * env
        return out


class Music:
    """Фоновая музыка заставки: mp3 встроен в этот файл (MUSIC_B64, в конце), играет по кругу.

    При первом запуске мелодия распаковывается во временный файл в папке данных приложения
    (Kivy загружает звук только из файла), дальше используется он же.
    """

    def __init__(self, cache_dir=None):
        self.sound = None
        path = self._extract(cache_dir)
        if path:
            self.sound = SoundLoader.load(path)
        if self.sound is not None:
            self.sound.loop = True
            self.sound.volume = 0.5

    @staticmethod
    def _extract(cache_dir):
        try:
            data = base64.b64decode(MUSIC_B64)
            folder = cache_dir or tempfile.gettempdir()
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, "MiniFB_menu_music.mp3")
            if not (os.path.isfile(path) and os.path.getsize(path) == len(data)):
                with open(path, "wb") as f:
                    f.write(data)
            return path
        except (OSError, ValueError):
            return None

    def play(self):
        if self.sound is None or not SETTINGS.music_on:
            return
        try:
            if self.sound.state != "play":
                self.sound.play()
        except Exception:
            pass

    def stop(self):
        if self.sound is not None:
            try:
                self.sound.stop()
            except Exception:
                pass


class Field(Widget):
    """Игровое поле: хранит всю логику и рисует на canvas."""

    GRID_X = 8
    GRID_Y = 8
    GOAL_COLUMNS = {3, 4}        # клетки ворот (для отрисовки)
    GOAL_POINTS = {3, 4, 5}      # узлы, в которые можно забить гол
    DIRECTIONS = {
        "up_left": (-1, -1),
        "up": (0, -1),
        "up_right": (1, -1),
        "down_left": (-1, 1),
        "down": (0, 1),
        "down_right": (1, 1),
    }
    PLAYER_DIRECTIONS = (
        "up_left", "up", "up_right",
        "down_left", "down", "down_right",
    )
    # Уровни сложности: пауза перед ходом компьютера и глубина просмотра ходов
    DIFFICULTIES = {
        "Easy":   {"delay": 0.5, "depth": 0},   # сначала вниз, без просмотра вперёд (бывают ничьи)
        "Normal": {"delay": 0.8, "depth": 2},   # 2 хода вперёд, нижние направления в приоритете
        "Hard":   {"delay": 1.2, "depth": 6},   # смотрит на 6 ходов вперёд
    }
    WIN_SCORE = 1000

    def __init__(self, ui, **kwargs):
        super().__init__(**kwargs)
        self.ui = ui  # ссылка на GameScreen (метки, кнопки, попап)
        self.score_player = 0
        self.score_computer = 0
        self.game_over = False
        self.job = None
        self.player_delay = 0.125                 # сек (авто-ход игрока)
        self.difficulty = "Easy"
        self.computer_delay = self.DIFFICULTIES[self.difficulty]["delay"]
        self.search_depth = self.DIFFICULTIES[self.difficulty]["depth"]
        self.ball = (4, 4)
        self.used_edges = set()
        self.visited_nodes = {self.ball}
        self.two_players = False          # режим «два игрока» на одном устройстве
        self.last_chain = []              # путь последней серии ходов одного игрока
        self.last_chain_owner = None
        self.current_player = "player"
        self.paused = False
        self.bind(pos=self.redraw, size=self.redraw)

    # ---------- состояние игры ----------
    def new_game(self, autostart=True):
        self.cancel_job()
        first_cpu = SETTINGS.first_move == "cpu" and not self.two_players   # вдвоём первым всегда игрок 1
        self.current_player = "computer" if first_cpu else "player"
        self.paused = False
        self.game_over = False
        self.ball = (4, 4)
        self.used_edges = set()
        self.visited_nodes = {self.ball}
        self.last_chain = []
        self.last_chain_owner = None
        self.ui.set_buttons(() if first_cpu else self.PLAYER_DIRECTIONS)
        self.set_status()
        self.redraw()
        if first_cpu and autostart:
            self.continue_game()          # первым ходит компьютер

    def set_difficulty(self, name):
        if name not in self.DIFFICULTIES:
            return
        self.difficulty = name
        self.computer_delay = self.DIFFICULTIES[name]["delay"]
        self.search_depth = self.DIFFICULTIES[name]["depth"]

    def cancel_job(self):
        if self.job is not None:
            self.job.cancel()
            self.job = None

    def set_status(self):
        ui = self.ui
        if self.game_over:
            ui.status_label.text = tr("game_over")
            ui.status_label.color = hexc("#ffd54a")
        elif self.paused:
            ui.status_label.text = tr("paused")
            ui.status_label.color = hexc("#ffd54a")
        elif self.two_players:
            first = self.current_player == "player"
            ui.status_label.text = tr("p1_move" if first else "p2_move")
            ui.status_label.color = hexc("#39FF14" if first else "#ff8a65")
        elif self.current_player == "player":
            ui.status_label.text = tr("your_move")
            ui.status_label.color = hexc("#39FF14")
        else:
            ui.status_label.text = tr("not_your_move")
            ui.status_label.color = hexc("#ff5252")

    def update_score(self):
        self.ui.score_label.text = f"{self.score_player} : {self.score_computer}"

    # ---------- правила ----------
    @staticmethod
    def edge_key(start, finish):
        return tuple(sorted((start, finish)))

    def is_goal(self, point):
        x, y = point
        return x in self.GOAL_POINTS and y in (-1, self.GRID_Y + 1)

    def is_inside_field(self, point):
        x, y = point
        return 0 <= x <= self.GRID_X and 0 <= y <= self.GRID_Y

    def is_valid_target(self, point):
        return self.is_inside_field(point) or self.is_goal(point)

    def legal_moves(self, directions=None, ball=None, used_edges=None):
        if directions is None:
            directions = self.DIRECTIONS.keys()
        if ball is None:
            ball = self.ball
        if used_edges is None:
            used_edges = self.used_edges
        moves = []
        x, y = ball
        min_goal_col = min(self.GOAL_COLUMNS)

        post_left_x = min_goal_col - 1
        post_right_x = max(self.GOAL_COLUMNS) + 1

        for direction in directions:
            dx, dy = self.DIRECTIONS[direction]
            target = (x + dx, y + dy)

            # Запрет ходов вверх/вниз вдоль боковых линий поля
            if x in (0, self.GRID_X) and direction in ("up", "down"):
                continue

            # Запрет "up_right" с верхней линии левее левой стойки верхних ворот
            if ball == (min_goal_col - 1, 0) and direction == "up_right":
                continue

            # Запрет "down_right" с нижней линии левее левой стойки нижних ворот
            if ball == (min_goal_col - 1, self.GRID_Y) and direction == "down_right":
                continue

            # Зеркальные запреты для правой штанги (чтобы не забивать вдоль штанги снаружи)
            if ball == (post_right_x + 1, 0) and direction == "up_left":
                continue
            if ball == (post_right_x + 1, self.GRID_Y) and direction == "down_left":
                continue

            # Дополнительные запреты возле штанг
            if y == 0 and x in (post_left_x, post_left_x + 1, post_right_x) and direction == "up":
                continue
            if y == self.GRID_Y and x in (post_right_x, post_right_x - 2) and direction == "down":
                continue

            if not self.is_valid_target(target):
                continue
            if self.edge_key(ball, target) in used_edges:
                continue
            moves.append(direction)
        return moves

    # ---------- ходы ----------
    def player_move(self, direction):
        if self.game_over or self.paused:
            return
        if self.current_player != "player" and not self.two_players:
            return
        if direction not in self.legal_moves(self.PLAYER_DIRECTIONS):
            return
        self.make_move(direction)

    def gives_extra_move(self, target, was_visited):
        x, y = target
        # Центр ворот: борта здесь нет, отскока нет -> ход переходит к сопернику
        goal_center_x = (min(self.GOAL_COLUMNS) + max(self.GOAL_COLUMNS) + 1) / 2
        on_goal_center = x == goal_center_x and y in (0, self.GRID_Y)
        bounced_from_border = (
            (x in (0, self.GRID_X) or y in (0, self.GRID_Y)) and not on_goal_center
        )
        border_rows = {i for i in range(1, self.GRID_Y) if i % 2 == 0}
        on_horizontal_border = y in border_rows
        return was_visited or bounced_from_border or on_horizontal_border

    def make_move(self, direction):
        start = self.ball
        dx, dy = self.DIRECTIONS[direction]
        target = (start[0] + dx, start[1] + dy)
        self.used_edges.add(self.edge_key(start, target))
        was_visited = target in self.visited_nodes
        # серия ходов одного игрока (доп. ходы продолжают её, смена игрока начинает новую)
        if self.last_chain_owner != self.current_player or not self.last_chain:
            self.last_chain = [start]
            self.last_chain_owner = self.current_player
        self.last_chain.append(target)
        self.ball = target
        if self.is_goal(target):
            self.finish_game("player" if target[1] == -1 else "computer")
            return
        self.visited_nodes.add(target)
        self.redraw()
        self.ui.sfx.play("move")
        if not self.gives_extra_move(target, was_visited):
            self.current_player = "computer" if self.current_player == "player" else "player"
        self.set_status()
        self.continue_game()

    def continue_game(self):
        if self.game_over:
            return
        if self.current_player == "player" or self.two_players:
            moves = self.legal_moves(self.PLAYER_DIRECTIONS)
            if not moves:
                self.finish_draw("no_moves")
                return
            if len(moves) == 1:
                self.ui.set_buttons(())
                self.job = Clock.schedule_once(
                    lambda dt, d=moves[0]: self.make_move(d), self.player_delay
                )
                return
            self.ui.set_buttons(moves)
            return
        self.ui.set_buttons(())
        moves = self.legal_moves()
        if not moves:
            self.finish_draw("no_moves")
            return
        # единственный (автоматический) ход — с той же скоростью, что у игрока
        delay = self.player_delay if len(moves) == 1 else self.computer_delay
        self.job = Clock.schedule_once(self.computer_move, delay)

    def computer_move(self, dt=None):
        self.job = None
        if self.game_over or self.paused or self.current_player != "computer":
            return
        moves = self.legal_moves()
        if not moves:
            self.finish_draw("no_moves")
            return
        if len(moves) == 1:
            self.make_move(moves[0])
            return

        self.make_move(self.choose_computer_move(moves))

    # ---------- ИИ компьютера ----------
    def choose_computer_move(self, moves):
        goal_y = self.GRID_Y + 1
        for m in moves:                       # забить гол, если можно
            dx, dy = self.DIRECTIONS[m]
            if self.ball[1] + dy == goal_y and self.is_goal((self.ball[0] + dx, goal_y)):
                return m

        if self.search_depth <= 0:
            # Easy: идёт вниз, если возможно, иначе по диагонали вниз, потом вверх.
            # Тупиков не избегает, поэтому партия может закончиться ничьей.
            priority = ["down", "down_left", "down_right", "up_left", "up", "up_right"]
            best_rank = min(priority.index(m) for m in moves)
            return random.choice([m for m in moves if priority.index(m) == best_rank])

        candidates = moves
        if self.difficulty == "Normal":
            # Normal: три нижних направления в приоритете, остальные — только если их нет
            down_moves = [m for m in moves if self.DIRECTIONS[m][1] > 0]
            if down_moves:
                candidates = down_moves

        scores = {
            m: self.move_value(self.ball, self.used_edges, self.visited_nodes,
                               "computer", m, self.search_depth,
                               -math.inf, math.inf)
            for m in candidates
        }
        best = max(scores.values())
        margin = 1.0 if self.difficulty == "Normal" else 0.01
        good = [m for m in candidates if scores[m] >= best - margin]
        return random.choice(good)

    def evaluate(self, ball):
        """Оценка позиции для компьютера: чем ниже и ближе к центру — тем лучше."""
        x, y = ball
        return y - 0.3 * abs(x - self.GRID_X / 2)

    def move_value(self, ball, used, visited, mover, direction, depth, alpha, beta):
        dx, dy = self.DIRECTIONS[direction]
        target = (ball[0] + dx, ball[1] + dy)
        if self.is_goal(target):
            bonus = self.WIN_SCORE + depth    # быстрый гол ценнее
            return bonus if target[1] > self.GRID_Y else -bonus
        extra = self.gives_extra_move(target, target in visited)
        next_mover = mover if extra else ("player" if mover == "computer" else "computer")
        return self.search(target, used | {self.edge_key(ball, target)},
                           visited | {target}, next_mover, depth - 1, alpha, beta)

    def search(self, ball, used, visited, mover, depth, alpha, beta):
        moves = self.legal_moves(ball=ball, used_edges=used)
        if not moves:
            return 0                          # ходов нет -> ничья
        if depth <= 0:
            return self.evaluate(ball)
        maximizing = mover == "computer"
        best = -math.inf if maximizing else math.inf
        for m in moves:
            val = self.move_value(ball, used, visited, mover, m, depth, alpha, beta)
            if maximizing:
                best = max(best, val)
                alpha = max(alpha, best)
            else:
                best = min(best, val)
                beta = min(beta, best)
            if beta <= alpha:
                break
        return best

    # ---------- конец игры ----------
    def finish_game(self, winner):
        self.game_over = True
        self.ui.set_buttons(())
        self.ui.sfx.play("goal")
        if winner == "player":
            self.score_player += 1
            text = tr("goal_p1" if self.two_players else "goal_win")
        else:
            self.score_computer += 1
            text = tr("goal_p2" if self.two_players else "goal_lose")
        self.update_score()
        self.set_status()
        self.redraw()
        self.ask_new_game(text)

    def finish_draw(self, reason):
        self.game_over = True
        self.ui.set_buttons(())
        self.ui.sfx.play("whistle")
        self.set_status()
        self.ask_new_game(f"{tr('draw')}\n{tr(reason)}")

    def ask_new_game(self, text):
        content = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
        content.add_widget(Label(
            text=f"{text}   |   {self.score_player} : {self.score_computer}\n{tr('new_game_q')}",
            halign="center", font_size=sp(15),
        ))
        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        yes = Button(text=tr("yes"))
        no = Button(text=tr("no"))
        row.add_widget(yes)
        row.add_widget(no)
        content.add_widget(row)

        # Компактное окно по центру экрана, без затемнения фона.
        popup = Popup(
            title=tr("game_over"), content=content,
            size_hint=(0.8, None), height=dp(170),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            auto_dismiss=False,
            background_color=(0, 0, 0, 0),
        )

        def on_yes(*_):
            popup.dismiss()
            self.new_game()

        def on_no(*_):
            popup.dismiss()
            App.get_running_app().show_menu()      # «Нет» — возврат в главное меню

        yes.bind(on_release=on_yes)
        no.bind(on_release=on_no)
        popup.open()

    # ---------- отрисовка ----------
    def geometry(self):
        width = max(self.width, 1)
        height = max(self.height, 1)

        field_width = width * 0.84
        field_height = height * 0.74
        cell = min(field_width / self.GRID_X, field_height / self.GRID_Y)

        margin_x = (width - cell * self.GRID_X) / 2
        margin_y = (height - cell * self.GRID_Y) / 2
        return margin_x, margin_y, cell, cell

    def point_to_pixel(self, point):
        """Логическая точка -> координаты Kivy (начало внизу слева, Y вверх)."""
        left, top, cell_x, cell_y = self.geometry()
        return (self.x + left + point[0] * cell_x,
                self.top - (top + point[1] * cell_y))

    def redraw(self, *args):
        self.canvas.clear()
        left, top, cell_x, cell_y = self.geometry()
        right = left + self.GRID_X * cell_x
        bottom = top + self.GRID_Y * cell_y

        # Локальные (tk-подобные, Y вниз) координаты -> Kivy
        def X(tx):
            return self.x + tx

        def Y(ty):
            return self.top - ty

        def line(x1, y1, x2, y2, color, width, cap="square"):
            Color(*hexc(color))
            Line(points=[X(x1), Y(y1), X(x2), Y(y2)], width=width, cap=cap)

        min_goal_col = min(self.GOAL_COLUMNS)
        max_goal_col = max(self.GOAL_COLUMNS)
        goal_left = left + min_goal_col * cell_x
        goal_right = left + (max_goal_col + 1) * cell_x
        goal_depth = cell_y

        with self.canvas:
            # фон
            Color(*hexc(GREEN))
            Rectangle(pos=self.pos, size=self.size)

            # полосы газона: чередуем светлый и тёмный зелёный по рядам клеток
            for row in range(self.GRID_Y):
                Color(*hexc(GREEN_LIGHT if row % 2 == 0 else GREEN))
                Rectangle(pos=(X(left), Y(top + (row + 1) * cell_y)),
                          size=(self.GRID_X * cell_x, cell_y))

            # боковые линии
            line(left, top, left, bottom, "#ffffff", 4)
            line(right, top, right, bottom, "#ffffff", 4)

            # верх
            line(left, top, goal_left, top, "#ffffff", 4)
            line(goal_right, top, right, top, "#ffffff", 4)

            # низ
            line(left, bottom, goal_left, bottom, "#ffffff", 4)
            line(goal_right, bottom, right, bottom, "#ffffff", 4)
            line(goal_left, bottom + cell_y, goal_right, bottom + cell_y, "#ffffff", 4)
            line(goal_left, bottom, goal_left, bottom + goal_depth, "#ffffff", 4)
            line(goal_right, bottom, goal_right, bottom + goal_depth, "#ffffff", 4)
            line(goal_left, bottom, goal_right, bottom, "#ffffff", 1)

            # внутренние клетки верхних ворот
            for gx in range(2):
                x0 = goal_left + gx * cell_x
                y0 = top - goal_depth
                Color(*hexc(GREEN))
                Rectangle(pos=(X(x0), Y(y0 + cell_y)), size=(cell_x, cell_y))
                Color(1, 1, 1, 1)
                Line(rectangle=(X(x0), Y(y0 + cell_y), cell_x, cell_y), width=1)

            # контур верхних ворот поверх клеток: одинаковая толщина 4, как у нижних
            line(goal_left, top, goal_left, top - goal_depth, "#ffffff", 4)
            line(goal_right, top, goal_right, top - goal_depth, "#ffffff", 4)
            line(goal_left, top - goal_depth, goal_right, top - goal_depth, "#ffffff", 4)

            # центральный круг
            cx, cy = self.point_to_pixel((self.GRID_X / 2, self.GRID_Y / 2))
            r = max(6, min(cell_x, cell_y) * 1.4)
            Color(*hexc("#e0e0e0"))
            Line(circle=(cx, cy, r), width=3)

            # сетка
            for x in range(1, self.GRID_X):
                px = left + x * cell_x
                line(px, top, px, bottom, "#c4e4c8", 1)
            for y in range(1, self.GRID_Y):
                py = top + y * cell_y
                line(left, py, right, py, "#ffffff", 4 if y % 2 == 0 else 1)

            # центральные линии ворот
            center_x = (goal_left + goal_right) / 2
            line(center_x, top - goal_depth, center_x, top, "#c4e4c8", 1)
            line(center_x, bottom, center_x, bottom + goal_depth, "#ffffff", 1)

            # подсветка пути последней серии ходов (как свечение у мяча)
            chain = self.last_chain
            for k_w, alpha in ((9, 0.07), (7, 0.10), (5, 0.16)):
                Color(1, 1, 0.7, alpha)
                for a, b in zip(chain, chain[1:]):
                    x1, y1 = self.point_to_pixel(a)
                    x2, y2 = self.point_to_pixel(b)
                    Line(points=[x1, y1, x2, y2], width=k_w * min(cell_x, cell_y) / 45.0,
                         cap="round")
            glow_r = max(8, min(cell_x, cell_y) * 0.13)
            for point in chain:
                gx, gy = self.point_to_pixel(point)
                for k, alpha in ((2.0, 0.07), (1.7, 0.10), (1.4, 0.16)):
                    Color(1, 1, 0.7, alpha)
                    Ellipse(pos=(gx - glow_r * k, gy - glow_r * k),
                            size=(2 * glow_r * k, 2 * glow_r * k))

            # пройденные рёбра
            Color(0, 0, 0, 1)
            for start, finish in self.used_edges:
                x1, y1 = self.point_to_pixel(start)
                x2, y2 = self.point_to_pixel(finish)
                Line(points=[x1, y1, x2, y2], width=2.5, cap="round")

            # посещённые узлы
            radius = max(5, min(cell_x, cell_y) * 0.095)
            ring = max(1.5, radius * 0.35)
            for point in self.visited_nodes:
                x, y = self.point_to_pixel(point)
                # белая обводка для контраста на зелёном фоне
                Color(1, 1, 1, 1)
                Ellipse(pos=(x - radius - ring, y - radius - ring),
                        size=(2 * (radius + ring), 2 * (radius + ring)))
                Color(0, 0, 0, 1)
                Ellipse(pos=(x - radius, y - radius), size=(2 * radius, 2 * radius))

            # мяч (тот же рисунок, что на заставке рядом с названием)
            bx, by = self.point_to_pixel(self.ball)
            br = max(10, min(cell_x, cell_y) * 0.19)

            # лёгкое свечение (несколько полупрозрачных кругов)
            for k, alpha in ((2.0, 0.07), (1.7, 0.10), (1.4, 0.16)):
                Color(1, 1, 0.7, alpha)
                Ellipse(pos=(bx - br * k, by - br * k), size=(2 * br * k, 2 * br * k))

            BallIcon.draw(bx, by, br)


class TagLabel(Label):
    """Надпись на скруглённой цветной подложке (элемент ТВ-плашки)."""

    def __init__(self, bg_color, radius=dp(6), **kwargs):
        super().__init__(**kwargs)
        self._radius = radius
        with self.canvas.before:
            self._bg_color = Color(*hexc(bg_color))
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size


class ScoreBoard(BoxLayout):
    """Плашка в стиле ТВ-трансляции: команды, счёт и строка статуса хода."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(4),
                         padding=(dp(6), dp(6), dp(6), dp(6)), **kwargs)
        with self.canvas.before:
            Color(*hexc("#0b1118"))
            self._shadow = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
            Color(*hexc("#16212e"))
            self._panel = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._sync, size=self._sync)

        top = BoxLayout(orientation="horizontal", spacing=dp(6))
        self.you_label = TagLabel(
            "#1358b8", text=tr("you"), bold=True, font_size=sp(20),
            color=(1, 1, 1, 1), size_hint_x=0.3,
        )
        top.add_widget(self.you_label)
        self.score_label = TagLabel(
            "#000000", text="0 : 0", bold=True, font_size=sp(32),
            color=(1, 1, 1, 1), size_hint_x=0.4,
        )
        top.add_widget(self.score_label)
        self.cpu_label = TagLabel(
            "#c62828", text=tr("cpu"), bold=True, font_size=sp(20),
            color=(1, 1, 1, 1), size_hint_x=0.3,
        )
        top.add_widget(self.cpu_label)
        self.add_widget(top)

        self.status_label = TagLabel(
            "#0b1118", text=tr("your_move"), bold=True, font_size=sp(20),
            color=hexc("#39FF14"), size_hint_y=None, height=dp(28),
        )
        self.add_widget(self.status_label)

    def _sync(self, *args):
        self._shadow.pos = (self.x - dp(1), self.y - dp(1))
        self._shadow.size = (self.width + dp(2), self.height + dp(2))
        self._panel.pos = self.pos
        self._panel.size = self.size


class ArrowButton(ButtonBehavior, Label):
    """Круглая полупрозрачная кнопка с тенью и плавной анимацией нажатия."""

    depth = NumericProperty(0)   # 0 — отпущена, 1 — нажата (анимируется)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw,
                  depth=self._redraw, disabled=self._redraw)
        self.bind(state=self._on_state)
        self._redraw()

    def _diameter(self):
        return min(self.width, self.height) * 0.92

    def collide_point(self, x, y):
        # нажатие засчитывается только внутри круга
        r = self._diameter() / 2
        return (x - self.center_x) ** 2 + (y - self.center_y) ** 2 <= r * r

    def _on_state(self, _w, state):
        Animation.cancel_all(self, "depth")
        if state == "down":
            Animation(depth=1, d=0.08, t="out_quad").start(self)
        else:
            Animation(depth=0, d=0.22, t="out_back").start(self)

    def _redraw(self, *args):
        p = self.depth
        off = self.disabled
        d = self._diameter() * (1 - 0.07 * p)      # при нажатии кнопка «проседает»
        r = d / 2
        cx, cy = self.center
        lift = dp(4) * (1 - p) + dp(1)            # тень прижимается при нажатии
        fade = 0.4 if off else 1.0

        self.canvas.before.clear()
        with self.canvas.before:
            # мягкая тень из нескольких слоёв
            for grow, alpha in ((dp(7), 0.07), (dp(4), 0.11), (dp(1.5), 0.16)):
                Color(0, 0, 0, alpha * fade * (1 - 0.4 * p))
                Ellipse(pos=(cx - r - grow, cy - r - grow - lift),
                        size=(d + 2 * grow, d + 2 * grow))
            # полупрозрачное тело
            Color(1, 1, 1, (0.22 if off else 0.55 + 0.2 * p))
            Ellipse(pos=(cx - r, cy - r), size=(d, d))
            # блик в верхней части
            Color(1, 1, 1, 0.16 * fade)
            Ellipse(pos=(cx - r * 0.78, cy - r * 0.05), size=(r * 1.56, r * 0.95))
            # светлая кромка
            Color(1, 1, 1, (0.35 if off else 0.9))
            Line(circle=(cx, cy, r), width=1.4)


class GameScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        with self.canvas.before:
            Color(*hexc(GREEN))
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        board = ScoreBoard(size_hint_y=None, height=dp(88))
        self.board = board
        self.score_label = board.score_label
        self.status_label = board.status_label
        self.add_widget(board)

        level_row = BoxLayout(orientation="horizontal",
                              padding=(dp(48), dp(2), dp(48), dp(6)),
                              size_hint_y=None, height=dp(42))
        self.level_row = level_row
        self.level_key = "Easy"          # внутреннее имя уровня (не зависит от языка)
        self.level_badge = LevelBadge()  # только показывает уровень; менять его в игре нельзя
        self.level_badge.set_level(self.level_key)
        level_row.add_widget(self.level_badge)
        self.add_widget(level_row)

        app = App.get_running_app()
        self.sfx = SoundFX(fallback_dir=os.path.join(app.user_data_dir, "sounds") if app else None)

        self.field = Field(self)
        self.add_widget(self.field)

        actions = BoxLayout(orientation="horizontal", spacing=dp(10),
                            padding=(dp(8), dp(4), dp(8), dp(6)),
                            size_hint_y=None, height=dp(50))
        self.pause_button = MenuButton(text=tr("pause"), font_size=sp(16), icon="pause")
        self.pause_button.bind(on_release=lambda *_: self.toggle_pause())
        self.menu_button = MenuButton(text=tr("to_menu"), font_size=sp(16),
                                      color=hexc("#c62828"), icon="home")
        self.menu_button.bind(on_release=lambda *_: self.confirm_exit())
        actions.add_widget(self.pause_button)
        actions.add_widget(self.menu_button)
        self.add_widget(actions)

        controls = GridLayout(cols=3, spacing=dp(6), padding=(dp(8), dp(4), dp(8), dp(8)),
                              size_hint_y=None, height=dp(150))
        labels = [
            ("↖", "up_left"), ("↑", "up"), ("↗", "up_right"),
            ("↙", "down_left"), ("↓", "down"), ("↘", "down_right"),
        ]
        self.buttons = {}
        for symbol, direction in labels:
            btn = ArrowButton(
                text=symbol, font_name=ARROW_FONT, font_size=sp(40), bold=True,
                color=hexc(BLUE), disabled_color=(0.35, 0.45, 0.4, 0.8),
            )
            btn.bind(on_release=lambda _b, d=direction: self.field.player_move(d))
            controls.add_widget(btn)
            self.buttons[direction] = btn
        self.add_widget(controls)

        self.field.new_game()

    def _update_bg(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def apply_language(self):
        """Перевод надписей игрового экрана после смены языка."""
        self._sync_mode()
        self.level_badge.set_level(self.level_key)
        self._sync_pause_button()
        self.menu_button.text = tr("to_menu")
        self.field.set_status()

    def _sync_mode(self):
        """Подписи и строка уровня зависят от режима: игра с компьютером или вдвоём."""
        two = self.field.two_players
        self.board.you_label.text = tr("player1" if two else "you")
        self.board.cpu_label.text = tr("player2" if two else "cpu")
        size = sp(14) if two else sp(20)
        self.board.you_label.font_size = size
        self.board.cpu_label.font_size = size
        self.level_row.opacity = 0 if two else 1      # уровень нужен только против компьютера
        self.level_row.disabled = two
        self.level_row.height = 0 if two else dp(42)

    def _sync_pause_button(self):
        paused = self.field.paused
        self.pause_button.text = tr("continue") if paused else tr("pause")
        self.pause_button.icon = "play" if paused else "pause"

    def toggle_pause(self):
        field = self.field
        if field.game_over:
            return
        field.paused = not field.paused
        self._sync_pause_button()
        field.set_status()
        if field.paused:
            field.cancel_job()           # отменяем запланированный ход
            self.set_buttons(())
        else:
            field.continue_game()        # продолжаем с того же места

    def confirm_exit(self):
        """Спрашивает «Да / Нет» перед выходом в главное меню. Пока окно открыто, игра на паузе."""
        if getattr(self, "_exit_popup", None) is not None:
            return
        field = self.field
        auto_paused = not field.paused and not field.game_over
        if auto_paused:
            self.toggle_pause()

        content = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
        content.add_widget(Label(text=tr("exit_q"), halign="center", font_size=sp(15)))
        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        yes = Button(text=tr("yes"))
        no = Button(text=tr("no"))
        row.add_widget(yes)
        row.add_widget(no)
        content.add_widget(row)

        popup = Popup(title=tr("to_menu"), content=content,
                      size_hint=(0.8, None), height=dp(190), auto_dismiss=False)
        self._exit_popup = popup

        def close():
            popup.dismiss()
            self._exit_popup = None

        def on_yes(*_):
            close()
            App.get_running_app().show_menu()

        def on_no(*_):
            close()
            if auto_paused and field.paused:
                self.toggle_pause()      # возвращаем игру, как было

        yes.bind(on_release=on_yes)
        no.bind(on_release=on_no)
        popup.open()

    def leave_game(self):
        """Выход в меню: останавливает партию и обнуляет счёт."""
        field = self.field
        field.score_player = field.score_computer = 0
        field.update_score()
        field.new_game(autostart=False)  # снимает паузу и отменяет отложенные ходы
        self._sync_pause_button()

    def start(self, level, two_players=False):
        """Запуск игры с выбранным на заставке уровнем (или вдвоём на одном устройстве)."""
        self.field.two_players = two_players
        self._sync_mode()
        self.level_key = level
        self.level_badge.set_level(level)
        self.field.set_difficulty(level)
        self.field.new_game()

    def set_buttons(self, enabled_directions):
        """Включает только перечисленные направления, остальные отключает."""
        for direction, btn in self.buttons.items():
            btn.disabled = direction not in enabled_directions


ICON_SLATE = "#37474f"
ICON_RED = "#c62828"
ICON_GRAY = "#b0bec5"
_QMARK_CACHE = {}

# Оформление уровней сложности: (нижний цвет градиента кнопки, цвет текста и звёзд)
LEVEL_LOOK = {
    "Easy": ((0.80, 0.95, 0.83), "#1b7a35"),
    "Normal": ((0.80, 0.89, 0.98), BLUE),
    "Hard": ((1.0, 0.84, 0.80), "#b3261e"),
}
LEVEL_ICON = {"Easy": "star1", "Normal": "star2", "Hard": "star3"}


def _draw_star(cx, cy, r, color):
    """Закрашенная пятиконечная звезда (веер треугольников от центра)."""
    Color(*color)
    verts = [cx, cy, 0, 0]
    for i in range(11):
        ang = math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        verts += [cx + rad * math.cos(ang), cy + rad * math.sin(ang), 0, 0]
    Mesh(vertices=verts, indices=list(range(len(verts) // 4)), mode="triangle_fan")


def draw_icon(kind, cx, cy, size, color):
    """Векторные иконки для кнопок: gear, help, power, pause, play, home."""
    r = size / 2.0
    if kind == "gear":
        Color(*hexc(ICON_SLATE))
        for i in range(8):
            a = i * math.pi / 4
            Line(points=[cx + 0.60 * r * math.cos(a), cy + 0.60 * r * math.sin(a),
                         cx + 0.98 * r * math.cos(a), cy + 0.98 * r * math.sin(a)],
                 width=r * 0.15, cap="none")
        Line(circle=(cx, cy, r * 0.62, 0, 360, 64), width=r * 0.10)
        Line(circle=(cx, cy, r * 0.27, 0, 360, 40), width=r * 0.08)
    elif kind == "help":
        Color(*hexc(ICON_RED))
        Ellipse(pos=(cx - r, cy - r), size=(size, size))
        key = int(size)
        tex = _QMARK_CACHE.get(key)
        if tex is None:
            lab = CoreLabel(text="?", font_size=max(8, int(size * 0.7)), bold=True)
            lab.refresh()
            tex = _QMARK_CACHE[key] = lab.texture
        Color(1, 1, 1, 1)
        Rectangle(texture=tex, pos=(cx - tex.width / 2.0, cy - tex.height / 2.0), size=tex.size)
    elif kind == "power":
        Color(*hexc(ICON_SLATE))
        Line(circle=(cx, cy, r * 0.66, 42, 318, 64), width=r * 0.10, cap="none")
        Line(points=[cx, cy + 0.12 * r, cx, cy + 0.98 * r], width=r * 0.10, cap="none")
    elif kind == "pause":
        Color(*color)
        bw, gap, h = size * 0.26, size * 0.20, size * 0.82
        RoundedRectangle(pos=(cx - gap / 2 - bw, cy - h / 2), size=(bw, h), radius=[bw * 0.3])
        RoundedRectangle(pos=(cx + gap / 2, cy - h / 2), size=(bw, h), radius=[bw * 0.3])
    elif kind == "play":
        Color(*color)
        Triangle(points=[cx - 0.30 * size, cy - 0.42 * size,
                         cx - 0.30 * size, cy + 0.42 * size,
                         cx + 0.44 * size, cy])
    elif kind == "people":
        Color(color[0], color[1], color[2], 0.55)          # второй игрок (позади)
        Ellipse(pos=(cx + 0.06 * size, cy + 0.02 * size), size=(0.36 * size, 0.36 * size))
        RoundedRectangle(pos=(cx + 0.0 * size, cy - 0.46 * size), size=(0.56 * size, 0.42 * size),
                         radius=[0.2 * size, 0.2 * size, 0.04 * size, 0.04 * size])
        Color(*color)                                      # первый игрок (впереди)
        Ellipse(pos=(cx - 0.40 * size, cy + 0.06 * size), size=(0.40 * size, 0.40 * size))
        RoundedRectangle(pos=(cx - 0.52 * size, cy - 0.46 * size), size=(0.64 * size, 0.46 * size),
                         radius=[0.22 * size, 0.22 * size, 0.04 * size, 0.04 * size])
    elif kind == "home":
        Color(*color)
        Triangle(points=[cx - 0.50 * size, cy + 0.02 * size, cx + 0.50 * size, cy + 0.02 * size,
                         cx, cy + 0.48 * size])
        Rectangle(pos=(cx - 0.34 * size, cy - 0.42 * size), size=(0.68 * size, 0.46 * size))
        Color(1, 1, 1, 0.9)
        Rectangle(pos=(cx - 0.09 * size, cy - 0.42 * size), size=(0.18 * size, 0.28 * size))


class MenuButton(ButtonBehavior, Widget):
    """Скруглённая полупрозрачная кнопка меню с необязательной иконкой.

    icon: "" | gear | help | power | pause | play | home | people | star1 | star2 | star3
    Иконка и надпись образуют одну группу по центру кнопки; звёзды стоят у левого
    края, надпись при этом центрируется по всей кнопке. Надпись рисуется прямо на
    canvas кнопки (без дочернего Label), поэтому не зависит от порядка раскладки
    и никогда не наезжает на иконку (если не помещается — сокращается «…»).
    """

    text = StringProperty("")
    icon = StringProperty("")
    font_size = NumericProperty(0)
    bold = BooleanProperty(True)
    color = ListProperty([0, 0, 0, 1])
    slide = NumericProperty(0)      # сдвиг по X (для анимации выезда), px
    pop = NumericProperty(1)        # масштаб (пружинка при нажатии)
    tint = ListProperty([0.80, 0.89, 0.98])   # нижний цвет градиента и «борт» кнопки (RGB 0..1)
    shine = NumericProperty(-1)     # положение блика 0..1 (вне диапазона — блика нет)
    _grad_cache = {}
    _shine_tex = None

    def __init__(self, **kwargs):
        kwargs.setdefault("bold", True)
        kwargs.setdefault("font_size", sp(22))
        kwargs.setdefault("color", hexc(BLUE))
        super().__init__(**kwargs)
        # Вся отрисовка кнопки идёт во вложенный canvas _body, а вокруг него стоят
        # постоянные матрицы: сдвиг + масштаб от центра. Анимация меняет только их,
        # не пересоздавая текстуры надписей.
        self._body = Canvas()
        with self.canvas.before:
            PushMatrix()
            self._tr_in = Translate(0, 0)
            self._sc = Scale(1, 1, 1)
            self._tr_out = Translate(0, 0)
        self.canvas.before.add(self._body)
        with self.canvas.before:                      # блик, бегущий по кнопке
            self._shine_col = Color(1, 1, 1, 0)
            self._shine = Quad(texture=self._shine_texture(),
                               points=[0, 0, 0, 0, 0, 0, 0, 0])
        with self.canvas.after:
            PopMatrix()
        self.bind(pos=self._update_xf, size=self._update_xf, slide=self._update_xf,
                  pop=self._update_xf, state=self._pop_on_press)
        self.bind(pos=self._update_shine, size=self._update_shine, shine=self._update_shine)
        self._update_xf()
        self.bind(pos=self._redraw, size=self._redraw, state=self._redraw,
                  icon=self._redraw, text=self._redraw, font_size=self._redraw,
                  bold=self._redraw, color=self._redraw, tint=self._redraw)
        self._redraw()
        Clock.schedule_once(self._redraw, 0)

    @classmethod
    def _gradient(cls, top, bottom):
        """Вертикальный градиент 1x32 (строка 0 — низ). Кэшируется по цветам."""
        key = (tuple(round(c, 3) for c in top), tuple(round(c, 3) for c in bottom))
        tex = cls._grad_cache.get(key)
        if tex is None:
            n = 32
            buf = bytearray()
            for i in range(n):
                f = i / (n - 1.0)
                for k in range(3):
                    buf.append(int(255 * (bottom[k] * (1 - f) + top[k] * f)))
                buf.append(255)
            tex = Texture.create(size=(1, n), colorfmt="rgba")
            tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
            tex.mag_filter = tex.min_filter = "linear"
            cls._grad_cache[key] = tex
        return tex

    @classmethod
    def _shine_texture(cls):
        """Горизонтальная полоса блика: прозрачно → белый → прозрачно."""
        if cls._shine_tex is None:
            n = 32
            buf = bytearray()
            for i in range(n):
                a = math.sin(math.pi * i / (n - 1.0)) ** 1.5
                buf += bytes((255, 255, 255, int(255 * a)))
            tex = Texture.create(size=(n, 1), colorfmt="rgba")
            tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
            tex.mag_filter = tex.min_filter = "linear"
            cls._shine_tex = tex
        return cls._shine_tex

    def flash(self):
        """Пускает по кнопке световой блик."""
        Animation.cancel_all(self, "shine")
        self.shine = 0
        anim = Animation(shine=1, d=0.8, t="in_out_quad")
        anim.bind(on_complete=lambda *_: setattr(self, "shine", -1))
        anim.start(self)

    def _update_shine(self, *args):
        p = self.shine
        if p < 0 or p > 1 or self.width <= 1:
            self._shine_col.a = 0
            return
        r, sw, slant = dp(14), dp(46), dp(14)
        x0 = self.x + r + max(0.0, self.width - 2 * r - sw - slant) * p
        y0, y1 = self.y + dp(3), self.top - dp(3)
        self._shine_col.a = 0.6 * math.sin(math.pi * p)
        self._shine.points = [x0, y0, x0 + sw, y0, x0 + sw + slant, y1, x0 + slant, y1]

    def _update_xf(self, *args):
        cx, cy = self.center
        self._tr_in.xy = (cx + self.slide, cy)
        self._sc.xyz = (self.pop, self.pop, 1)
        self._tr_out.xy = (-cx, -cy)

    def _pop_on_press(self, _w, state):
        Animation.cancel_all(self, "pop")
        if state == "down":
            self.flash()
            Animation(pop=0.95, d=0.07, t="out_quad").start(self)
        else:
            Animation(pop=1.0, d=0.35, t="out_elastic").start(self)

    def _make_label(self, width=None):
        """Текстура надписи (белая; цвет задаётся Color на canvas)."""
        opts = dict(text=self.text, font_size=self.font_size, bold=self.bold)
        if width is not None:
            opts.update(text_size=(width, None), shorten=True, shorten_from="right",
                        halign="center")
        lab = CoreLabel(**opts)
        lab.refresh()
        return lab

    def _redraw(self, *args):
        kind = self.icon
        icon_cx = None
        icon_size = 0
        text_x, text_w = self.x, self.width
        shorten_w = None                      # ширина окна для «…», если места мало
        text_tex = None
        if self.text:
            text_tex = self._make_label().texture
        if text_tex is not None and kind and not kind.startswith("star"):
            icon_size = min(self.height * 0.52, dp(26))
            gap = dp(8)
            margin = dp(6)
            group = icon_size + gap + text_tex.width
            start = (self.width - group) / 2.0
            if start >= margin:
                icon_cx = self.x + start + icon_size / 2.0
                text_x = self.x + start + icon_size + gap
                text_w = text_tex.width
            else:                             # узкая кнопка: сокращаем надпись
                icon_cx = self.x + margin + icon_size / 2.0
                text_x = self.x + margin + icon_size + gap
                text_w = max(dp(20), self.right - margin - text_x)
                shorten_w = text_w
                text_tex = self._make_label(shorten_w).texture

        pressed = self.state == "down"
        r = dp(14)
        tint = tuple(self.tint[:3])
        edge = tuple(c * 0.62 for c in tint)                  # тёмный «борт» снизу
        if pressed:
            top = tuple(c + (1 - c) * 0.35 for c in tint)
            bottom = tuple(c * 0.90 for c in tint)
        else:
            top, bottom = (1.0, 1.0, 1.0), tint
        lip = dp(1.5) if pressed else dp(4.5)                 # толщина «борта»
        self._body.clear()
        with self._body:
            for k, a in ((3, 0.05), (2, 0.07), (1, 0.09)):   # мягкая тень
                g = k * dp(1.3)
                Color(0, 0, 0, a)
                RoundedRectangle(pos=(self.x - g, self.y - lip - g),
                                 size=(self.width + 2 * g, self.height + 2 * g), radius=[r + g])
            Color(*edge, 1)                                   # объёмный нижний борт
            RoundedRectangle(pos=(self.x, self.y - lip), size=self.size, radius=[r])
            Color(1, 1, 1, 1)                                 # корпус с градиентом
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r],
                             texture=self._gradient(top, bottom))
            Color(1, 1, 1, 0.20 if pressed else 0.45)         # глянцевый отсвет сверху
            RoundedRectangle(pos=(self.x + dp(3), self.center_y + dp(1)),
                             size=(self.width - dp(6), self.height / 2 - dp(4)),
                             radius=[r - dp(2), r - dp(2), dp(5), dp(5)])
            Color(*edge, 0.85)                                # внешний контур
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, r), width=1.1)
            Color(1, 1, 1, 0.9)                               # светлая внутренняя кромка
            Line(rounded_rectangle=(self.x + dp(1.5), self.y + dp(1.5), self.width - dp(3),
                                    self.height - dp(3), r - dp(1.5)), width=1.1)
            if kind.startswith("star"):
                n = int(kind[4:] or 0)
                sz = min(self.height * 0.40, dp(20))
                step = sz * 1.15
                x0 = self.x + dp(16) + sz / 2
                for i in range(3):
                    col = tuple(self.color[:3]) + (1,) if i < n else hexc(ICON_GRAY)
                    _draw_star(x0 + i * step, self.center_y, sz / 2, col)
            elif icon_cx is not None:
                draw_icon(kind, icon_cx, self.center_y, icon_size, self.color)
            if text_tex is not None:
                tw, th = text_tex.size
                Color(1, 1, 1, 0.85)                       # светлая подложка под буквами
                Rectangle(texture=text_tex,
                          pos=(int(text_x + (text_w - tw) / 2.0), int(self.center_y - th / 2.0) - 1),
                          size=(tw, th))
                Color(*self.color)
                Rectangle(texture=text_tex,
                          pos=(int(text_x + (text_w - tw) / 2.0), int(self.center_y - th / 2.0)),
                          size=(tw, th))


class LevelBadge(MenuButton):
    """Табличка с текущим уровнем сложности на игровом экране.

    Выглядит как кнопки меню (градиент, борт, звёзды), но не реагирует на касания:
    выбрать уровень можно только на заставке перед началом игры."""

    def __init__(self, **kwargs):
        kwargs.setdefault("font_size", sp(17))
        super().__init__(**kwargs)

    def set_level(self, key):
        tint, col = LEVEL_LOOK.get(key, LEVEL_LOOK["Normal"])
        self.tint = list(tint)
        self.color = hexc(col)
        self.icon = LEVEL_ICON.get(key, "")
        self.text = f"{tr('level')} {tr('level_' + key)}"

    def on_touch_down(self, touch):
        return False

    def on_touch_move(self, touch):
        return False

    def on_touch_up(self, touch):
        return False


class BallIcon(Widget):
    """Объёмный футбольный мяч (усечённый икосаэдр), нарисованный на canvas.

    12 чёрных пятиугольников проецируются на шар, поэтому у края они сплющены;
    поверх лежит текстура освещения: тень на нижнем правом краю и блик сверху слева.
    """

    ALPHA = 0.353          # угловой радиус пятиугольника
    SIZE_RATIO = 0.8       # диаметр мяча относительно меньшей стороны виджета
    _model = None          # (пятиугольники, швы) — считается один раз
    _shade = None          # текстура освещения — создаётся один раз

    @staticmethod
    def _norm(v):
        n = math.sqrt(sum(c * c for c in v))
        return tuple(c / n for c in v)

    @staticmethod
    def _dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    @classmethod
    def _build_model(cls):
        if cls._model is not None:
            return cls._model
        phi = (1 + math.sqrt(5)) / 2
        raw = []
        for s1 in (1, -1):
            for s2 in (1, -1):
                raw += [(0, s1, s2 * phi), (s1, s2 * phi, 0), (s2 * phi, 0, s1)]

        def rot_x(p, t):
            x, y, z = p
            return (x, y * math.cos(t) - z * math.sin(t), y * math.sin(t) + z * math.cos(t))

        def rot_y(p, t):
            x, y, z = p
            return (x * math.cos(t) + z * math.sin(t), y, -x * math.sin(t) + z * math.cos(t))

        centers = []
        for v in raw:
            v = rot_x(cls._norm(v), math.atan(1 / phi))   # один пятиугольник — к зрителю
            v = rot_x(rot_y(v, 0.45), 0.30)                # лёгкий наклон
            centers.append(v)

        neighbors = [[j for j in range(12)
                      if j != i and abs(cls._dot(centers[i], centers[j]) - 1 / math.sqrt(5)) < 0.05]
                     for i in range(12)]

        a = cls.ALPHA
        pentagons = []
        for i, c in enumerate(centers):
            b = centers[neighbors[i][0]]
            d = cls._dot(c, b)
            e1 = cls._norm(tuple(b[k] - d * c[k] for k in range(3)))   # к соседнему пятиугольнику
            e2 = (c[1] * e1[2] - c[2] * e1[1],
                  c[2] * e1[0] - c[0] * e1[2],
                  c[0] * e1[1] - c[1] * e1[0])
            verts = []
            for k in range(5):
                t = 2 * math.pi * k / 5
                verts.append(tuple(math.cos(a) * c[m]
                                   + math.sin(a) * (math.cos(t) * e1[m] + math.sin(t) * e2[m])
                                   for m in range(3)))
            pentagons.append((c, verts))

        seams = []
        for i in range(12):
            for j in neighbors[i]:
                if j > i:
                    pa = max(pentagons[i][1], key=lambda p: cls._dot(p, centers[j]))
                    pb = max(pentagons[j][1], key=lambda p: cls._dot(p, centers[i]))
                    seams.append((pa, pb))
        cls._model = (pentagons, seams)
        return cls._model

    @classmethod
    def _shade_texture(cls):
        if cls._shade is not None:
            return cls._shade
        n = 96
        lx, ly, lz = cls._norm((-0.45, 0.55, 0.70))      # направление света (сверху слева)
        hx, hy, hz = cls._norm((lx, ly, lz + 1.0))       # вектор блика
        buf = bytearray()
        for j in range(n):                                # строка 0 — нижняя
            v = -1 + 2 * (j + 0.5) / n
            for i in range(n):
                u = -1 + 2 * (i + 0.5) / n
                r = math.sqrt(u * u + v * v)
                edge = min(1.0, max(0.0, (1.0 - r) * n / 2))   # сглаживание края круга
                if edge <= 0:
                    buf += b"\x00\x00\x00\x00"
                    continue
                z = math.sqrt(max(0.0, 1.0 - r * r))
                diff = max(0.0, u * lx + v * ly + z * lz)
                dark = (1.0 - diff) ** 1.3 * 0.55
                dark += (1.0 - dark) * (1.0 - z) ** 3 * 0.3     # затемнение у края
                spec = max(0.0, u * hx + v * hy + z * hz) ** 40 * 0.85
                alpha = spec + dark * (1.0 - spec)
                c = int(255 * spec / alpha) if alpha > 0 else 0
                buf += bytes((c, c, c, int(255 * alpha * edge)))
        tex = Texture.create(size=(n, n), colorfmt="rgba")
        tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
        tex.mag_filter = "linear"
        tex.min_filter = "linear"
        cls._shade = tex
        return tex

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    @classmethod
    def draw(cls, cx, cy, r):
        """Рисует мяч в текущем canvas-контексте: центр (cx, cy), радиус r (в пикселях).
        Используется и заставкой (рядом с названием), и игровым полем."""
        d = 2 * r
        pentagons, seams = cls._build_model()
        # тень на земле под мячом
        for kw, kh, alpha in ((1.25, 0.30, 0.08), (1.0, 0.22, 0.12), (0.7, 0.14, 0.18)):
            Color(0, 0, 0, alpha)
            w, h = d * kw, d * kh
            Ellipse(pos=(cx - w / 2 + d * 0.06, cy - r - h * 0.3), size=(w, h))
        # белый шар
        Color(0.98, 0.98, 0.98, 1)
        Ellipse(pos=(cx - r, cy - r), size=(d, d))
        # швы
        Color(0.07, 0.07, 0.09, 1)
        seam_w = max(1.0, r * 0.06)
        for pa, pb in seams:
            if pa[2] > 0.02 and pb[2] > 0.02:
                Line(points=[cx + r * pa[0], cy + r * pa[1],
                             cx + r * pb[0], cy + r * pb[1]], width=seam_w)
        # пятиугольники (у края сплющены проекцией)
        for center, verts in pentagons:
            if center[2] < -0.1:
                continue
            pts = []
            for x, y, z in verts:
                if z < 0:                           # вершина за горизонтом — на край круга
                    m = math.hypot(x, y) or 1.0
                    x, y = x / m, y / m
                pts.append((cx + r * x, cy + r * y))
            mx = sum(p[0] for p in pts) / 5
            my = sum(p[1] for p in pts) / 5
            vertices = [mx, my, 0, 0]
            for x, y in pts + pts[:1]:
                vertices += [x, y, 0, 0]
            Mesh(vertices=vertices, indices=list(range(7)), mode="triangle_fan")
        # освещение: объём, блик
        Color(1, 1, 1, 1)
        Rectangle(texture=cls._shade_texture(), pos=(cx - r, cy - r), size=(d, d))
        # контур
        Color(0.12, 0.12, 0.14, 0.9)
        Line(circle=(cx, cy, r), width=max(1.0, r * 0.07))

    def _redraw(self, *args):
        d = min(self.width, self.height) * self.SIZE_RATIO
        self.canvas.clear()
        with self.canvas:
            self.draw(self.center_x, self.center_y + dp(2), d / 2)


class ShimmerTitle(Label):
    """Название с переливающимся радужным цветом. Касание ускоряет перелив и «подпрыгивает»,
    а движение пальца/мыши по надписи сдвигает волну цвета."""

    def __init__(self, title_text, **kwargs):
        kwargs["markup"] = True
        kwargs.setdefault("outline_width", max(2, int(dp(2))))          # тёмный контур букв
        kwargs.setdefault("outline_color", (0.03, 0.2, 0.08, 1))
        super().__init__(**kwargs)
        self.title_text = title_text
        self.base_size = self.font_size
        self.max_size = self.font_size
        with self.canvas.before:               # мягкая тень под буквами
            Color(0, 0, 0, 0.4)
            self._shadow = Rectangle()
        self.bind(texture=self._sync_shadow, pos=self._sync_shadow, size=self._sync_shadow)
        self.phase = 0.0
        self.boost = 0.0
        self._tick(0)
        Clock.schedule_interval(self._tick, 1 / 30)

    def _sync_shadow(self, *args):
        tex = self.texture
        if tex is None:
            self._shadow.size = (0, 0)
            return
        tw, th = tex.size
        off = dp(3)
        self._shadow.texture = tex
        self._shadow.size = (tw, th)
        self._shadow.pos = (self.center_x - tw / 2 + off, self.center_y - th / 2 - off)

    def fit_to(self, width):
        """Уменьшает шрифт, если название не помещается в ширину рядом с мячом."""
        n = max(len(self.title_text), 1)
        size = min(self.max_size, max(sp(20), width / (n * 0.5)))
        if abs(size - self.base_size) > 0.5:
            self.base_size = size
            Animation.cancel_all(self, "font_size")
            self.font_size = size

    def _tick(self, dt):
        self.boost *= 0.92 ** (dt * 60)           # ускорение от касания плавно затухает
        self.phase = (self.phase + dt * (0.12 + self.boost)) % 1.0
        n = max(len(self.title_text), 1)
        parts = []
        for i, ch in enumerate(self.title_text):
            r, g, b = colorsys.hsv_to_rgb((self.phase + 0.8 * i / n) % 1.0, 0.55, 1.0)
            parts.append(f"[color={int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}]{ch}[/color]")
        self.text = "".join(parts)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        touch.grab(self)
        self.boost = 2.5
        Animation.cancel_all(self, "font_size")
        (Animation(font_size=self.base_size * 1.15, d=0.1, t="out_quad")
         + Animation(font_size=self.base_size, d=0.25, t="out_back")).start(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self.phase = (self.phase + touch.dx / max(self.width, 1)) % 1.0
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)


class TitleRow(Widget):
    """Мяч + название: центрируются на экране как единая группа (по видимой ширине текста)."""

    GAP = dp(14)
    drop = NumericProperty(0)     # высота «падения» мяча при появлении
    bob = NumericProperty(0)      # лёгкое покачивание мяча

    def __init__(self, ball, title, **kwargs):
        super().__init__(**kwargs)
        self.ball, self.title = ball, title
        for w in (ball, title):
            w.size_hint = (None, None)
            self.add_widget(w)
        self.bind(pos=self._layout, size=self._layout, drop=self._layout, bob=self._layout)
        title.bind(texture_size=self._layout)
        self._layout()

    def _layout(self, *args):
        ball, title = self.ball, self.title
        ball.size = (dp(46), self.height)
        ball_vis = ball.width * BallIcon.SIZE_RATIO          # видимый диаметр мяча
        margin = (ball.width - ball_vis) / 2                 # пустое поле внутри виджета мяча
        title.fit_to(self.width - ball_vis - self.GAP)
        tw = title.texture_size[0]
        title.size = (tw, self.height)
        total = ball_vis + self.GAP + tw
        # лёгкая поправка влево: тень названия смещена вправо
        x0 = self.x + (self.width - total) / 2 - dp(1.5)
        ball.pos = (x0 - margin, self.y + self.drop + self.bob)
        title.pos = (x0 + ball_vis + self.GAP, self.y + self.drop * 0.25)


class SettingsPopup(Popup):
    """Окно настроек: звук в игре, музыка заставки, язык интерфейса."""

    def __init__(self, **kwargs):
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))

        self.sound_switch = Switch(active=SETTINGS.sound_on, size_hint_x=0.35)
        self.sound_switch.bind(active=self._on_sound)
        self.sound_label = self._add_row(content, "sound", self.sound_switch)

        self.music_switch = Switch(active=SETTINGS.music_on, size_hint_x=0.35)
        self.music_switch.bind(active=self._on_music)
        self.music_label = self._add_row(content, "music", self.music_switch)

        names = [name for _code, name in Settings.LANGUAGES]
        current = dict(Settings.LANGUAGES)[SETTINGS.lang]
        self.lang_spinner = Spinner(text=current, values=names, font_size=sp(17),
                                    size_hint_x=0.5)
        self.lang_spinner.bind(text=self._on_language)
        self.lang_label = self._add_row(content, "language", self.lang_spinner)

        first_box = BoxLayout(size_hint_x=0.5, spacing=dp(6))
        self.first_buttons = {}
        for code, key in (("you", "you"), ("cpu", "cpu")):
            tb = ToggleButton(text=tr(key), group="first_move", allow_no_selection=False,
                              state="down" if SETTINGS.first_move == code else "normal",
                              font_size=sp(16))
            tb.bind(state=lambda _b, st, c=code: self._on_first(c, st))
            first_box.add_widget(tb)
            self.first_buttons[code] = tb
        self.first_label = self._add_row(content, "first_move", first_box)

        self.close_button = Button(text=tr("close"), size_hint_y=None, height=dp(44))
        content.add_widget(self.close_button)

        super().__init__(title=tr("settings_title"), content=content,
                         size_hint=(0.9, None), height=dp(370), **kwargs)
        self.close_button.bind(on_release=self.dismiss)

    @staticmethod
    def _add_row(parent, key, control):
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        label = Label(text=tr(key), font_size=sp(17), halign="left", valign="middle")
        label.bind(size=lambda w, size: setattr(w, "text_size", size))
        row.add_widget(label)
        row.add_widget(control)
        parent.add_widget(row)
        return label

    def _on_sound(self, _switch, value):
        SETTINGS.sound_on = value
        SETTINGS.save()
        app = App.get_running_app()
        if value and app is not None:
            app.game.sfx.play("move")           # короткий отклик: звук включён

    def _on_music(self, _switch, value):
        SETTINGS.music_on = value
        SETTINGS.save()
        app = App.get_running_app()
        if app is not None:
            app.apply_music_setting()

    def _on_first(self, code, state):
        if state == "down" and SETTINGS.first_move != code:
            SETTINGS.first_move = code
            SETTINGS.save()

    def _on_language(self, _spinner, name):
        code = next((c for c, n in Settings.LANGUAGES if n == name), None)
        if code is None or code == SETTINGS.lang:
            return
        app = App.get_running_app()
        if app is not None:
            app.set_language(code)
        self.apply_language()

    def apply_language(self):
        self.title = tr("settings_title")
        self.sound_label.text = tr("sound")
        self.music_label.text = tr("music")
        self.lang_label.text = tr("language")
        self.first_label.text = tr("first_move")
        self.first_buttons["you"].text = tr("you")
        self.first_buttons["cpu"].text = tr("cpu")
        self.close_button.text = tr("close")


class SplashScreen(BoxLayout):
    """Заставка: живой фон (бегущие полосы газона, всплывающие огоньки, пульсирующее
    свечение за названием), поочерёдно «выезжающие» кнопки и падающий мяч."""

    SPARKS = 18

    def __init__(self, on_pick, on_two=None, **kwargs):
        super().__init__(orientation="vertical", padding=(dp(28), dp(30), dp(28), dp(16)),
                         spacing=dp(14), **kwargs)
        self.on_pick = on_pick
        self._t = 0.0
        self._tick_ev = None
        self._intro_evs = []
        self._glint_ev = None
        self._glint_i = 0

        with self.canvas.before:
            Color(*hexc(GREEN))
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*hexc(GREEN_LIGHT))
            self._stripes = [Rectangle() for _ in range(7)]
            self._glow_cols, self._glows = [], []
            for _ in range(3):                                   # свечение за названием
                self._glow_cols.append(Color(1, 1, 0.85, 0.06))
                self._glows.append(Ellipse())
            rnd = random.Random(7)
            self._sparks = []
            for _ in range(self.SPARKS):                         # плывущие вверх огоньки
                col = Color(1, 1, 1, 0.1)
                self._sparks.append(dict(
                    col=col, el=Ellipse(), x=rnd.random(), y=rnd.random(),
                    v=rnd.uniform(0.03, 0.08), r=rnd.uniform(dp(3), dp(11)),
                    ph=rnd.uniform(0, 6.28), a=rnd.uniform(0.12, 0.3)))
        self.bind(pos=self._paint, size=self._paint)

        self.add_widget(Widget(size_hint_y=0.6))
        self.title_row = TitleRow(
            BallIcon(), ShimmerTitle("MiniFootball", bold=True, font_size=sp(64)),
            size_hint_y=None, height=dp(80),
        )
        self.add_widget(self.title_row)
        self.choose_label = Label(
            text=tr("choose_level"), font_size=sp(20),
            color=(1, 1, 1, 0.9), size_hint_y=None, height=dp(34),
        )
        self.add_widget(self.choose_label)
        self.level_buttons = []
        for level in Field.DIFFICULTIES:
            look = LEVEL_LOOK.get(level, LEVEL_LOOK["Normal"])
            btn = MenuButton(text=tr("level_" + level), size_hint_y=None, height=dp(56),
                             tint=look[0], color=hexc(look[1]),
                             icon={"Easy": "star1", "Normal": "star2", "Hard": "star3"}.get(level, ""))
            btn.bind(on_release=lambda _b, lv=level: self.on_pick(lv))
            self.add_widget(btn)
            self.level_buttons.append((level, btn))

        self.two_button = MenuButton(text=tr("two_players"), size_hint_y=None, height=dp(52),
                                     font_size=sp(20), icon="people",
                                     tint=(0.90, 0.85, 0.98), color=hexc("#5e35b1"))
        self.two_button.bind(on_release=lambda *_: on_two() if on_two else None)
        self.add_widget(self.two_button)

        bottom = BoxLayout(orientation="horizontal", spacing=dp(14),
                           size_hint_y=None, height=dp(48))
        self.rules_button = MenuButton(text=tr("rules"), font_size=sp(18),
                                       color=hexc("#c62828"), icon="help",
                                       tint=(1.0, 0.88, 0.86))
        self.rules_button.bind(on_release=lambda *_: self.show_rules())
        self.settings_button = MenuButton(text=tr("settings"), font_size=sp(18),
                                          color=hexc("#37474f"), icon="gear",
                                          tint=(0.86, 0.90, 0.93))
        self.settings_button.bind(on_release=lambda *_: self.show_settings())
        bottom.add_widget(self.rules_button)
        bottom.add_widget(self.settings_button)
        self.add_widget(bottom)

        self.add_widget(Widget(size_hint_y=1))
        self.copy_label = Label(
            text=" \u00a9 2026 Gleb Vysotsky. All rights reserved", bold=True, font_size=sp(16),
            color=(1, 1, 1, 1), size_hint_y=None, height=dp(28),
        )
        self.add_widget(self.copy_label)

        # порядок появления: (виджет, как появляется)
        self._items = [(self.title_row, "drop"), (self.choose_label, "fade")]
        for i, (_lv, btn) in enumerate(self.level_buttons):
            self._items.append((btn, "left" if i % 2 == 0 else "right"))
        self._items += [(self.two_button, "left"), (self.rules_button, "left"),
                        (self.settings_button, "right"),
                        (self.copy_label, "fade")]

    # ---------- анимация фона ----------
    def _paint(self, *args):
        """Рисует фон для текущего момента времени self._t."""
        if not hasattr(self, "title_row"):                       # виджеты ещё не созданы
            return
        w, h = self.size
        self._bg.pos, self._bg.size = self.pos, self.size
        if w <= 1 or h <= 1:
            return
        t = self._t
        sh = h / 10.0
        base = self.y - 2 * sh + (t * dp(12)) % (2 * sh)         # полосы медленно ползут вверх
        for i, rect in enumerate(self._stripes):
            y0 = max(base + (2 * (i - 1) + 1) * sh, self.y)
            y1 = min(base + (2 * (i - 1) + 2) * sh, self.top)
            if y1 <= y0:
                rect.size = (0, 0)
            else:
                rect.pos, rect.size = (self.x, y0), (w, y1 - y0)

        cx, cy = self.title_row.center                           # «дышащее» свечение
        pulse = 0.5 + 0.5 * math.sin(t * 1.8)
        vis = self.title_row.opacity
        for j, (col, el) in enumerate(zip(self._glow_cols, self._glows)):
            rw = dp(150) * (1 + 0.55 * j) * (0.94 + 0.06 * pulse)
            rh = rw * 0.5
            col.a = (0.09 - 0.025 * j) * (0.6 + 0.4 * pulse) * vis
            el.pos, el.size = (cx - rw / 2, cy - rh / 2), (rw, rh)

        for s in self._sparks:                                   # огоньки
            x = self.x + (s["x"] + 0.025 * math.sin(t * 0.7 + s["ph"])) * w
            y = self.y + s["y"] * h
            r = s["r"] * (0.9 + 0.1 * math.sin(t * 1.3 + s["ph"]))
            fade = max(0.0, min(1.0, s["y"] * 5, (1.0 - s["y"]) * 5))
            s["col"].a = s["a"] * fade
            s["el"].pos, s["el"].size = (x - r, y - r), (2 * r, 2 * r)

    def _tick(self, dt):
        self._t += dt
        for s in self._sparks:
            s["y"] += s["v"] * dt
            if s["y"] > 1.0:
                s["y"] = 0.0
                s["x"] = random.random()
        self.title_row.bob = dp(3) * math.sin(self._t * 2.2)     # мяч слегка покачивается
        self._paint()

    # ---------- анимация появления ----------
    def play_intro(self):
        """Запускает фон и поочерёдное появление элементов (вызывается при показе меню)."""
        self.stop_anim(final=False)
        span = max(self.width, dp(300))
        for idx, (widget, kind) in enumerate(self._items):
            Animation.cancel_all(widget)
            widget.opacity = 0
            if kind == "drop":
                widget.drop = dp(150)
            elif kind in ("left", "right"):
                widget.slide = -span * 0.7 if kind == "left" else span * 0.7
            self._intro_evs.append(
                Clock.schedule_once(partial(self._launch, widget, kind), 0.12 + 0.085 * idx))
        self._tick_ev = Clock.schedule_interval(self._tick, 1 / 30)
        self._glint_ev = Clock.schedule_interval(self._glint, 1.3)

    def _glint(self, _dt):
        """По очереди пускает блик по кнопкам меню."""
        btns = [b for _lv, b in self.level_buttons] + [
            self.two_button, self.rules_button, self.settings_button]
        btns[self._glint_i % len(btns)].flash()
        self._glint_i += 1

    @staticmethod
    def _launch(widget, kind, _dt):
        Animation(opacity=1, d=0.35, t="out_quad").start(widget)
        if kind == "drop":
            Animation(drop=0, d=1.0, t="out_bounce").start(widget)          # мяч падает и отскакивает
        elif kind in ("left", "right"):
            Animation(slide=0, d=0.65, t="out_back").start(widget)          # кнопка выезжает с пружинкой

    def stop_anim(self, final=True):
        """Останавливает фон и таймеры; при final=True возвращает все элементы в обычный вид."""
        for ev in self._intro_evs:
            ev.cancel()
        self._intro_evs = []
        if self._tick_ev is not None:
            self._tick_ev.cancel()
            self._tick_ev = None
        if self._glint_ev is not None:
            self._glint_ev.cancel()
            self._glint_ev = None
        if final:
            for widget, kind in self._items:
                Animation.cancel_all(widget)
                widget.opacity = 1
                if kind == "drop":
                    widget.drop = 0
                elif kind in ("left", "right"):
                    widget.slide = 0
                    widget.pop = 1

    def apply_language(self):
        """Перевод надписей заставки после смены языка."""
        self.choose_label.text = tr("choose_level")
        for level, btn in self.level_buttons:
            btn.text = tr("level_" + level)
        self.two_button.text = tr("two_players")
        self.rules_button.text = tr("rules")
        self.settings_button.text = tr("settings")

    def show_settings(self):
        SettingsPopup().open()

    def show_rules(self):
        label = Label(text=tr("rules_text"), font_size=sp(15), halign="left", valign="top",
                      size_hint_y=None, padding=(dp(4), dp(4)))
        label.bind(width=lambda w, v: setattr(w, "text_size", (v - dp(8), None)))
        label.bind(texture_size=lambda w, ts: setattr(w, "height", ts[1] + dp(8)))
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(label)

        close = Button(text=tr("close"), size_hint_y=None, height=dp(44))
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        content.add_widget(scroll)
        content.add_widget(close)

        popup = Popup(title=tr("rules_title"), content=content, size_hint=(0.92, 0.85))
        close.bind(on_release=popup.dismiss)
        popup.open()


class SafeRoot(BoxLayout):
    """Отодвигает игру от системных панелей Android (статус-бар сверху, навигация снизу).
    С target API 35+ Android рисует приложение под панелями, поэтому отступы берём из WindowInsets."""

    def __init__(self, child, **kw):
        super().__init__(**kw)
        self._tries = 0
        self.add_widget(child)
        if platform == "android":
            Clock.schedule_interval(self._apply_insets, 0.25)

    def _apply_insets(self, _dt):
        self._tries += 1
        top = bottom = 0
        try:
            from jnius import autoclass
            act = autoclass("org.kivy.android.PythonActivity").mActivity
            ins = act.getWindow().getDecorView().getRootWindowInsets()
            if ins is not None:
                top = ins.getSystemWindowInsetTop()
                bottom = ins.getSystemWindowInsetBottom()
        except Exception:
            pass
        if top or bottom:
            self.padding = [0, top, 0, bottom]
            return False  # получили значения - перестаём опрашивать
        return self._tries < 20


class MiniFootballApp(App):
    title = "MiniFootball"

    def build(self):
        SETTINGS.load(self.user_data_dir)
        self.music = Music(cache_dir=os.path.join(self.user_data_dir, "music"))
        self.manager = ScreenManager(transition=FadeTransition(duration=0.25))
        self.game = GameScreen()

        splash_screen = Screen(name="splash")
        self.splash = SplashScreen(on_pick=self.start_game, on_two=self.start_two_players)
        splash_screen.add_widget(self.splash)
        game_screen = Screen(name="game")
        game_screen.add_widget(self.game)

        self.manager.add_widget(splash_screen)
        self.manager.add_widget(game_screen)
        Window.clearcolor = hexc(GREEN)
        return SafeRoot(self.manager)

    def on_start(self):
        self.music.play()
        Clock.schedule_once(lambda _dt: self.splash.play_intro(), 0)

    def on_stop(self):
        self.music.stop()

    def show_menu(self):
        self.game.leave_game()
        self.manager.current = "splash"
        self.splash.play_intro()
        self.apply_music_setting()

    def set_language(self, code):
        SETTINGS.lang = code
        SETTINGS.save()
        self.splash.apply_language()
        self.game.apply_language()

    def apply_music_setting(self):
        """Включает или выключает музыку заставки сразу после смены настройки."""
        if SETTINGS.music_on and self.manager.current == "splash":
            self.music.play()
        else:
            self.music.stop()

    def start_game(self, level, two_players=False):
        self.music.stop()
        self.game.start(level, two_players)
        self.manager.current = "game"
        self.splash.stop_anim()

    def start_two_players(self):
        self.start_game("Easy", two_players=True)


# Встроенная мелодия меню (MiniFB.mp3, base64). Заменить музыку: закодировать новый mp3 в base64
# и вставить сюда вместо содержимого скобок.
MUSIC_B64 = (
    "SUQzBAAAAAAtTVRTU0UAAAAPAAADTGF2ZjYwLjE2LjEwMABHRU9CAAAtKgAAA2FwcGxpY2F0aW9uL2MycGEAYzJwYQBjMnBhIG1h"
    "bmlmZXN0IHN0b3JlAAAAFn9qdW1iAAAAHmp1bWRjMnBhABEAEIAAAKoAOJtxA2MycGEAAAAWWWp1bWIAAABHanVtZGMybWEAEQAQ"
    "gAAAqgA4m3EDdXJuOmMycGE6ODJiZGQwZjItMmJiYy00YmY3LWJhYmYtZmExNWFhZDQxZWM3AAAAA5RqdW1iAAAAKWp1bWRjMmFz"
    "ABEAEIAAAKoAOJtxA2MycGEuYXNzZXJ0aW9ucwAAAAC5anVtYgAAAERqdW1kY2JvcgARABCAAACqADibcRNjMnBhLmluZ3JlZGll"
    "bnQudjMAAAAAGGMyc2i5hiYvbe5IzwuT8Dgy+r5iAAAAbWNib3KjaWRjOmZvcm1hdGphdWRpby9tcGVnamluc3RhbmNlSUR4LHht"
    "cDppaWQ6ZGFkZjNjYjgtNTYyYS00OGEzLWFmMjItMzQwNDRjMjRkNDY0bHJlbGF0aW9uc2hpcGhwYXJlbnRPZgAAAeJqdW1iAAAA"
    "QWp1bWRjYm9yABEAEIAAAKoAOJtxE2MycGEuYWN0aW9ucy52MgAAAAAYYzJzaJDeXemSA0UQAxqMjiWup1UAAAGZY2JvcqJnYWN0"
    "aW9uc4KiZmFjdGlvbmtjMnBhLm9wZW5lZGpwYXJhbWV0ZXJzoWtpbmdyZWRpZW50c4GiY3VybHgtc2VsZiNqdW1iZj1jMnBhLmFz"
    "c2VydGlvbnMvYzJwYS5pbmdyZWRpZW50LnYzZGhhc2hYIPGxPFF6INNITHqOPNuSZQz2qnc2WsL593gq+++edJtfpGZhY3Rpb254"
    "HWNvbS5hbnRocm9waWMuY2xhdWRlLnByb3ZpZGVkanBhcmFtZXRlcnOheB9jb20uYW50aHJvcGljLm9yaWdpbi1jb25maWRlbmNl"
    "Z3Vua25vd25rZGVzY3JpcHRpb254ZkNsYXVkZSBwcm92aWRlZCB0aGlzIGZpbGUgYXQgdGhlIHJlcXVlc3Qgb2YgYSB1c2VyIGFu"
    "ZCBtYXkgaGF2ZSBjcmVhdGVkIG9yIG1vZGlmaWVkIHRoZSBmaWxlIGNvbnRlbnRzLm1zb2Z0d2FyZUFnZW50oWRuYW1lZkNsYXVk"
    "ZXJhbGxBY3Rpb25zSW5jbHVkZWT1AAAAyGp1bWIAAABAanVtZGNib3IAEQAQgAAAqgA4m3ETYzJwYS5oYXNoLmRhdGEAAAAAGGMy"
    "c2grVeBQz7r3RpApAB67Wu6jAAAAgGNib3KlY2FsZ2ZzaGEyNTZjcGFkTQAAAAAAAAAAAAAAAABkaGFzaFggXWWy1HS+eM09C9mK"
    "C/KPrRk21NOVgnptsBAl2FnIMMBkbmFtZW5qdW1iZiBtYW5pZmVzdGpleGNsdXNpb25zgaJlc3RhcnQYWGZsZW5ndGgZFn8AAAI+"
    "anVtYgAAACdqdW1kYzJjbAARABCAAACqADibcQNjMnBhLmNsYWltLnYyAAAAAg9jYm9ypWNhbGdmc2hhMjU2aXNpZ25hdHVyZXhN"
    "c2VsZiNqdW1iZj0vYzJwYS91cm46YzJwYTo4MmJkZDBmMi0yYmJjLTRiZjctYmFiZi1mYTE1YWFkNDFlYzcvYzJwYS5zaWduYXR1"
    "cmVqaW5zdGFuY2VJRHgseG1wOmlpZDoyNzI4MDhjMS0wOGJkLTQ3MjktODIxZC1kMDU3MWJmZWI4YzhyY3JlYXRlZF9hc3NlcnRp"
    "b25zg6JjdXJseC1zZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmluZ3JlZGllbnQudjNkaGFzaFgg8bE8UXog00hMeo48"
    "25JlDPaqdzZawvn3eCr77550m1+iY3VybHgqc2VsZiNqdW1iZj1jMnBhLmFzc2VydGlvbnMvYzJwYS5hY3Rpb25zLnYyZGhhc2hY"
    "IK0+R8abM3Ab2pEohgFu+neHMZ/IftiUx22Ul1Zlx4PeomN1cmx4KXNlbGYjanVtYmY9YzJwYS5hc3NlcnRpb25zL2MycGEuaGFz"
    "aC5kYXRhZGhhc2hYIN/+N84GDEtPasFtETPsLIG+f1Wm8Vn/n5+ZZYW5+W2JdGNsYWltX2dlbmVyYXRvcl9pbmZvo2RuYW1lb0Fu"
    "dGhyb3BpYyBGaWxlc2d2ZXJzaW9uZTEuMC4wa3NwZWNWZXJzaW9uZTIuNC4wAAAQOGp1bWIAAAAoanVtZGMyY3MAEQAQgAAAqgA4"
    "m3EDYzJwYS5zaWduYXR1cmUAAAAQCGNib3LShFkCEqIBJhghWQIKMIICBjCCAY2gAwIBAgIUQOWgCu7COdC+uIP6BkIFPWdVEwAw"
    "CgYIKoZIzj0EAwMwSTEXMBUGA1UEChMOQW50aHJvcGljLCBQQkMxLjAsBgNVBAMTJUFudGhyb3BpYyBDb250ZW50IENyZWRlbnRp"
    "YWxzIFJvb3QgQ0EwHhcNMjYwODA3MTg0MzU2WhcNMjgwODA2MTk0MzU2WjBEMRcwFQYDVQQKEw5BbnRocm9waWMsIFBCQzEpMCcG"
    "A1UEAxMgQW50aHJvcGljIENsYXVkZSBDb250ZW50IFNpZ25pbmcwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAASYegpry1AYBRTV"
    "NL1CpTlbROnY3dey+UrsF9C3phYrATN3ZHf93Mo8RQN0KOUuOn19P4oWNFWe5n2/She9N7eTo1gwVjAOBgNVHQ8BAf8EBAMCB4Aw"
    "FQYDVR0lBA4wDAYKKwYBBAGD6F4CATAMBgNVHRMBAf8EAjAAMB8GA1UdIwQYMBaAFM5R4gSBTmRbI/jjxM+aPpzB11zCMAoGCCqG"
    "SM49BAMDA2cAMGQCMDFzHRSeAXrSy1WOzkbhPZ6Km2wGTmZ/2gK18k8BQGXyqz88Rdrz6CTX9flAnYNVxgIwcF9c3fVhqmJKpi+U"
    "hasNUMko69cyX6STPfta3Q8EjyzDjzoyrol46FP6VFHhvUcJoWNwYWRZDZ4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "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"
    "LTooJI6jJAWkBJIWBNqqNOtg1INjf/sSosP61QwDgAxJmPbIxYvNbFjBAoVqBq6bOyN9WuR8xghGiyenXTaU3cGAqQCbsBR+MI3G"
    "I3OyPnKjIQFjZ5fsswHVACU8kMUkLasokv/zgsRIK+KSfAVbyAAxU0XzotgoVFmGLVTPBQ6xWtdsjJB6ics5/qJq2T//GYAGQy70"
    "swxq0+P/nJ8oMQjU9P4fnzt/+R6VWggqgs5Zay7j//moeJO2Pt6y/W7lqy8IUDShy5/////7o38n9f/////0M4/5FWgmY3E61Eqh"
    "CKRENCAAA+TEN2vAzcMMmVEkQNnw4IXMDjbFAEjd0aUJrjIQwdcEmhgpAIPMYMyPJdd8aBoErGpoSmgPAJLoZmSbDBsmokNNWYOA"
    "xZEBgAyMoMYp//OCxFxCwu66X5rIA5A4XHMA2uBl1cIKDyyPhaCMOSoPAUhkSgFhKxvZgrGTmBwiQ7OYeaZAz2IoP0lc3Nmql61U"
    "z4MUUZPAlIygSBdxrgkmADBIRIt54fZ2rPOxGNP/GV0R5kU00xxHRjav5ZbatDer9l6Cz4syZZLIjSqItQMuZp6DSIiwDHXsb4st"
    "EmwNabu0d7lF5VB0gsNMjcxAlfvef///+Z4LY3cVO5L4NMj0gt8///4xLKSb+LoC84AKBlbEvpEQAU0Mvc8YKP+xuPz/84LEFSti"
    "qsGH2XgB3DNHGDjBt0taznfsyxOPYkd4p4jxdBQlTL69xbk+1VPNeexLP3g2Dzhw2U/aG6j1G/Q+JtVtMpym+zLaffLB+PFlIRVA"
    "ZUaRXItQJ1NISyqzJaqEXeaVMsjRpZRx7H4r0SZC7ZSwmEzC6opJI5FGmdx8yJI/2hC6wVSX1Op2JU5rxY0ikioo+plfe8G2c2x8"
    "/7+/f2eyFTcVMAMIkVRQQRIQaHZS0c+KEX09V+Cs/gsQKHCpK5rk/IaWnd5UtytvO9VpX//zgsQrK2qmtETL2TngYe/t6MsDesTQ"
    "jMYGGC2ssylgi7Jt7WZgN6NY7VSkk/EZlG4r5O0ulVQwQUiyvYh5qpPK5yS0DBhE0USheNsFlViQRTCqe8Y9qInIRpvXB1yoFPqB"
    "1BcFpRJ84S2uyREFaYMey6US4La1LT9/VdK+oPwwPkZ08/ebW6bWzvy1pZxMqgiCgGFtrBtgLemEBUxKIkA4KCCVWmqunrOUCp49"
    "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"
    "iNmraFHYwqdJhyTwmmibPGTL27tkRgyMcQiowwQzuGYaeKHqOz/fyzy7/dcyrZd/8GfK4sWTK5MFAbMWQmMG0COmRxMqBcMCQzMC"
    "wJMKAgNcBrBglmU5fjWaGDw0GN5PmFYKgkBxECpkMG5MArQ5uZBILmFJegJVRUMC//OCxEY8WrZkAV3YAAKUhGBgKCJdEJscqghi"
    "pk74HIimzayOiSHMBE5TQytMhAYcRilQJXFALE2BioKFRiRuKkssMIRg4WIMjBmCx6YjAoFBcXiEr1EAYYGhl7+OHMVafVqXSqDG"
    "GGECRqa4hc5tTH5TyXXZVtrAGtlRS/5d9Tmu0kEFAQYAMsmm7+fKHLuFHOmBkBo4st+d7hfrZWvrSgwMoIhJ7rtajs/l3+f/87//"
    "//////Whm8pyf5yuSayyVccARILYUpgwNqAB3TAQaLL/84LEGDGK5qR/mcABVREmk0QikeGGRWXFBUJVuioKSxtsxf5psGoczIF3"
    "VvpdNak7UWcSpRJLGZfpQ4rFQRZGceazKanxs1SQ9RfQBSqU2GYjZJmmjS2ZxpVAi9B/F9U01FG2Ypi0l4l0L0TThDqcJQQnnyVn"
    "2eN1WZq34zLg8v3X2itSWOpft28mHT2/vT38uSLL8YJsb+g5/67/4Y0Vv4xMxeL4f/////77////////////////YvdEVQEHHBEH"
    "FEWCwGBSgAQgB4BhAeUgs//zgsQVMQrm1b+YwANmV+6CvHDWFac9tVA02SjSwRECWRA2zVTRTaFdqP1MROHKVnV3TusbqyqVz74M"
    "0VlaTFp+PKJDwYg6sPxpm+85fQse5uKQhfSnDgxhQfDHV7CvW19PFL9y1PRGLUT/v+seQOu91XPWdiksYV6lutVzt0P2ocvNLyYm"
    "15SDoLubT2IQ5U/tun5yiw3jhja+7llfu/r/3ylUshynlcbn88/////xrVv/X//////7s4TLKiBAyohsBS4few1TQdUgQdVeQaIj"
    "//OCxBQqKn60JdnAAPCXflTvCsR2JsebaB5p+LVMtizG7X25zkfDPS2zqxP/yCbk3jzuduAVIL+znYzSV6fN0anO0/Zdalbex2ii"
    "29WaeGpVftS7O5ctQPdubi07PVH1mLNeiiFyXQKyiIxKjfmOSSa+kk7+ztl74FttLfuiovjd+cm4ZtallWMcmW5UVLLa0tvxzdSl"
    "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"
    "W6xAFTSAtTzj//OCxCgxyopoJ1zYAPNpQBYCxOV/FEmYDbitIUOTZLU3ARUGazFqXnJvHHcxBS1CqToiMEsWdvrctdzk2LI2ngEd"
    "DtMSEZUoCyStRXbnaTLXzSYQGDp//5jaxxpJe12kWDMUQzRg9AZnhnhlXscqbp6SpIIF13ncse03L1qiUqROQ1hzPPDuOstc/LFu"
    "yg0Kx/+//75/6eJQF5cufcjVuyVd5L/4P8octh/lDlUASgIXCYBgETBQPCUaAGiEGYo/4cI/0aX38SI45n34dQCxgEj/84LEJDTD"
    "copfj5gBCaKYyvDiwbGAwGOSQwg3IqVxPAoFIulIy84eIIF+wGgTIvGJHfAVCHtjaFLidRbCcDZg94RyQ0iJDjL+eG2FqQ9xIliL"
    "lg+bENJkqkOMjcuo/8mESQGbGy5gs8X58uGhAiaMzy1GRkmXTFD/+skSfMCsThfKpPlwnioXy6Vy4ZJJooqSSWitT1t//5FiQHPI"
    "CSQzBDiRGbI0nhwEoTo4yPJocBDCZIPtjYrjYrFoCUxBTUUzLjEwMFVVVVVVVVVVVVVVVf/zgsQVAAADSAHAAABVVVVVVVVVVVVV"
    "VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
    "VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
    "VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
)


if __name__ == "__main__":
    MiniFootballApp().run()
