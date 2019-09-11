#! /usr/bin/env python3

import logging
import numpy as np
import os
import sys
import time
from gomoku import AI
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QRadioButton,
                             QGroupBox, QGridLayout, QHBoxLayout, QVBoxLayout)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QTimer


class ChessPiece(QPushButton):
    BLACK = 1
    WHITE = -1

    def __init__(self, row, col, size=32):
        super().__init__()
        self.row = row
        self.col = col
        self.setFixedWidth(size)
        self.setFixedHeight(size)
        self.color = None

    def drop(self, color):
        if self.color is not None:
            return
        half_size = self.width() / 2
        if color == ChessPiece.BLACK:
            self.setStyleSheet(f'background-color: black; border-radius: {half_size}px;')
            self.color = color
            logging.info(f'BLACK ({self.row}, {self.col})')
        elif color == ChessPiece.WHITE:
            self.setStyleSheet(f'background-color: white; border-radius: {half_size}px;')
            self.color = color
            logging.info(f'WHITE ({self.row}, {self.col})')
        else:
            raise ValueError('Invalid color')

    def reset(self):
        self.color = None
        self.setStyleSheet('')


class MainWindow(QWidget):
    trigger_ai = pyqtSignal()

    def __init__(self, size=16, parent=None):
        super(QWidget, self).__init__(parent=parent)
        self.chessboard_size = size

        self.choose_black = QRadioButton('Black')
        self.choose_white = QRadioButton('White')
        self.choose_black.setChecked(True)
        self.choose_black.toggled.connect(self.refresh_board)
        # self.choose_white.clicked.connect(self.refresh_board)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.choose_black)
        input_layout.addWidget(self.choose_white)
        input_group = QGroupBox('Your color')
        input_group.setLayout(input_layout)

        self.chessboard_panel = self._init_chessboard_panel()
        layout = QVBoxLayout()
        layout.addWidget(input_group)
        layout.addLayout(self.chessboard_panel)
        self.setLayout(layout)

        self.trigger_ai.connect(self.ai_play)
        self.refresh_board()

    def _init_chessboard_panel(self):
        size = self.chessboard_size
        self.chessboard_pos = [[ChessPiece(row, col) for col in range(size)] for row in range(size)]
        board_layout = QGridLayout()
        for row in range(size):
            for col in range(size):
                this = self.chessboard_pos[row][col]
                this.clicked.connect(lambda: self.human_play(self.sender()))
                board_layout.addWidget(this, row, col)
        return board_layout

    def refresh_board(self):
        logging.warning('Refreshing chessboard')
        if self.choose_white.isChecked():
            self.human_color = ChessPiece.WHITE
            logging.info('Your chess color: white')
        else:
            self.human_color = ChessPiece.BLACK
            logging.info('Your chess color: black')
        self._init_game()

    def _init_game(self):
        self.ai = AI(self.chessboard_size, -self.human_color, 5)  # -human_color: AI color
        self.chessboard = np.zeros((self.chessboard_size, self.chessboard_size))

        # clean chessboard
        for row in self.chessboard_pos:
            for piece in row:
                if piece.color is not None:
                    piece.reset()

        if self.human_color == ChessPiece.WHITE:
            self.trigger_ai.emit()

    def human_play(self, piece):
        piece.drop(self.human_color)
        QTimer.singleShot(1, lambda: self.trigger_ai.emit())

    def ai_play(self):
        self.chessboard_panel.setEnabled(False)
        self.ai.go(self.chessboard)
        # time.sleep(1)
        new_row, new_col = self.ai.candidate_list[-1]
        self.chessboard_pos[new_row][new_col].drop(-self.human_color)
        self.chessboard_panel.setEnabled(True)


def main():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s %(levelname)s] %(message)s')
    app = QApplication(sys.argv)
    app.setApplicationName('Gomoku Desktop')
    if os.name == 'nt':
        app.setFont(QFont('Segoe UI'))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
