#! /usr/bin/env python3

import logging
import numpy as np
import sys
from enum import IntEnum
from gomoku import AI
from PyQt5.QtCore import QCoreApplication, QObject, QEventLoop, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QMessageBox,
                             QGridLayout, QLayout, QHBoxLayout, QVBoxLayout)
from typing import Optional, Tuple
from scipy.signal import correlate


class Color(IntEnum):
    BLACK = -1
    WHITE = 1


class ChessPiece(QPushButton):
    def __init__(self, row: int, col: int, size=32):
        super().__init__()
        self.coordinate = (row, col)
        self.color = None
        self.setFixedWidth(size)
        self.setFixedHeight(size)

    def drop(self, color: Color):
        assert self.color is None
        assert color in {Color.BLACK, Color.WHITE}
        self.color = color
        self.setStyleSheet(f'background-color: {color.name.lower()}; border-radius: {self.width()/2}px;')
        logging.info(f'{color.name} {self.coordinate}')
        QCoreApplication.processEvents()  # refresh ui immediately

    def clear(self):
        self.color = None
        self.setStyleSheet('')


class ChessBoard(QWidget):
    dropped = pyqtSignal(int, int)

    def __init__(self, data: np.ndarray, parent=None):
        super(QWidget, self).__init__(parent=parent)
        self.data = data
        row, col = data.shape
        self.pieces = np.empty(data.shape, dtype=object)
        layout = QGridLayout()
        for c in range(col):
            layout.addWidget(QLabel('%3d' % c), 0, c+1)
        for r in range(row):
            layout.addWidget(QLabel('%3d' % r), r+1, 0)
            for c in range(col):
                this = self.pieces[r, c] = ChessPiece(r, c)
                this.clicked.connect(lambda: self._on_click(self.sender()))
                layout.addWidget(this, r+1, c+1)
        self.setLayout(layout)
        layout.setSizeConstraint(QLayout.SetFixedSize)

    def place(self, coordinate: Tuple[int, int], color: Color):
        self.pieces[coordinate].drop(color)

    def _on_click(self, piece: ChessPiece):
        if piece.color is None:
            self.dropped.emit(*piece.coordinate)
        else:
            QMessageBox.warning(self, 'Invalid Position', 'This position has been occupied!')


class Player(QObject):
    dropped = pyqtSignal(int, int)

    def __init__(self, color: Color):
        super().__init__()
        self.chessboard = None
        self.color = color

    def play(self, color: Color):
        if color == self.color:
            self.dropped.emit(*self._drop())

    def _drop(self) -> Tuple[int, int]:
        raise NotImplementedError

    def set_chessboard(self, chessboard_data: np.ndarray):
        self.chessboard = chessboard_data


class AIPlayer(Player):
    def __init__(self, color: Color, ai):
        super().__init__(color)
        self.ai = ai

    def _drop(self) -> Tuple[int, int]:
        self.ai.go(self.chessboard)
        return self.ai.candidate_list[-1]


class HumanPlayer(Player):
    def __init__(self, color: Color, board: ChessBoard):
        super().__init__(color)
        self.board = board
        self.choice = None

    def _drop(self) -> Tuple[int, int]:
        loop = QEventLoop()
        # don't change the order of connect, as slots are executed in the same order
        self.board.dropped.connect(self.__choose)
        self.board.dropped.connect(loop.quit)
        self.board.setEnabled(True)
        loop.exec()  # block until the "dropped" signal is triggered
        self.board.setEnabled(False)
        self.board.dropped.disconnect()
        return self.choice

    def __choose(self, row, col):
        self.choice = (row, col)


class MainWindow(QWidget):
    drop = pyqtSignal(Color)

    def __init__(self, size=15, parent=None):
        super().__init__(parent=parent)
        self.chessboard_data = np.zeros((size, size), dtype=np.int8)
        self.chessboard_panel = ChessBoard(self.chessboard_data)

        self.start_btn = QPushButton('Start')
        self.stop_btn = QPushButton('Stop')
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)

        self.setWindowTitle('Gomoku Desktop')
        self.chessboard_panel.setEnabled(False)
        layout = QVBoxLayout()
        layout.addWidget(self.chessboard_panel)
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.stop_btn)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
        layout.setSizeConstraint(QLayout.SetFixedSize)

        self.is_playing = False
        self.players = {}
        self.current_color = Color.BLACK

    @property
    def is_playing(self):
        return self._is_playing

    @is_playing.setter
    def is_playing(self, val):
        self._is_playing = val
        self.start_btn.setDisabled(val)
        self.stop_btn.setEnabled(val)

    def set_player(self, color: Color, player: Player):
        player.set_chessboard(self.chessboard_data)
        self.players[color] = player

    def start(self):
        self.is_playing = True
        logging.info('Gomoku game starts')
        for player in self.players.values():
            self.drop.connect(player.play)
            player.dropped.connect(self.receive)
        self.judge()
        self.next(self.is_playing)

    def receive(self, row: int, col: int):
        self.chessboard_panel.place((row, col), self.current_color)
        self.chessboard_data[row, col] = self.current_color
        self.judge()
        self.current_color = Color(-self.current_color)
        self.next(self.is_playing)

    def stop(self):
        self.is_playing = False
        self.chessboard_panel.setEnabled(False)
        self.next(False)

    def next(self, playing: bool):
        if playing:
            self.drop.emit(self.current_color)
        else:
            for player in self.players.values():
                self.drop.disconnect(player.play)
                player.dropped.disconnect(self.receive)

    def judge(self):
        winner = self._check_winner()
        if winner:
            QMessageBox.information(self, 'Game Finished', f'Winner: {winner.name}')
            self.is_playing = False
        elif np.count_nonzero(self.chessboard_data == 0) == 0:  # no empty position
            QMessageBox.information(self, 'Game Finished', 'Draw')
            self.is_playing = False

    def _check_winner(self) -> Optional[Color]:
        """:return: color of the winner. `None` if unfinished or for a draw"""
        patterns = [
            np.ones(5, dtype=np.int8).reshape(1, 5),
            np.ones(5, dtype=np.int8).reshape(5, 1),
            np.eye(5, dtype=np.int8),
            np.fliplr(np.eye(5, dtype=np.int8))
        ]
        black = (self.chessboard_data == Color.BLACK).astype(np.int8)
        white = (self.chessboard_data == Color.WHITE).astype(np.int8)
        black_win = max([np.max(correlate(black, p, mode='same')) for p in patterns]) == 5
        white_win = max([np.max(correlate(white, p, mode='same')) for p in patterns]) == 5
        if black_win == white_win:  # draw
            return None
        elif black_win:
            return Color.BLACK
        else:  # white_win
            return Color.WHITE


def main():
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s %(levelname)s] %(message)s')
    app = QApplication(sys.argv)
    chessboard_length = 15
    win = MainWindow(chessboard_length)
    win.set_player(Color.BLACK, HumanPlayer(Color.BLACK, win.chessboard_panel))
    win.set_player(Color.WHITE, AIPlayer(Color.WHITE, AI(chessboard_length, Color.WHITE, -1)))
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
