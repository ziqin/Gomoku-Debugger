import numpy as np
import time
from typing import Tuple


class Color:
    BLACK = -1
    WHITE = 1
    NONE = 0


class AI:
    np.random.seed(0)

    def __init__(self, chessboard_size, color, time_out):
        self.chessboard_size = chessboard_size
        self.color = color          # you are white or black
        self.time_out = time_out    # the algorithm's running time must not exceed the time limit
        self.candidate_list = []    # append your decision into candidate_list
        self.last_chessboard = np.zeros((chessboard_size, chessboard_size))

    def go(self, chessboard: np.ndarray) -> None:
        """
        :param chessboard: current chessboard
        :return: None
        """
        self.candidate_list.clear()
        drop_pos = self.play(chessboard)
        assert chessboard[drop_pos] == Color.NONE
        self.candidate_list.append(drop_pos)
        self.last_chessboard = chessboard

    def play(self, chessboard: np.ndarray) -> Tuple[int,int]:
        """
        :param chessboard: the chessboard presented to the AI
        :return: the coordinate where the AI will drop
        """
        # randomly select an empty position
        xs, ys = np.where(chessboard == Color.NONE)
        indexes = list(zip(xs, ys))
        return indexes[np.random.randint(len(indexes))]
