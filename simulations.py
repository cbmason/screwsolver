#!/usr/bin/env python

"""
simulations.py

Various simulations for profiling the game
"""

from cards import Rank
from database import DBInterface
from distutils import util
from screw_your_neighbor import SYNGame, SYNPlayer
from strategies import SYNStrat_naive_firstonly, SYNStrat_cheater_villain

from argparse import ArgumentParser

import logging
import sys


FIRSTPOS_SIMPLE_NAME = "firstpos_fullspec_"
DEFAULT_DB_NAME = "data/SYNDB.db"
DEFAULT_ITERS = 100000


class SYNSimulation:
    """Base class for simulations"""

    def __init__(self, name, dbname, table_sz, num_of_iters):
        """Takes name of the sim, DB to store it, table size, and number of iterations"""
        self._num_of_iters = num_of_iters
        self.current_iter = 1
        self.game = SYNGame(name, dbname, num_seats=table_sz)

    def run(self, consoleprint=False):
        """Run the sim"""
        for i in range(1, self._num_of_iters + 1):
            self._step()
            if (i % 100) == 0:
                sys.stdout.write(f"Running iteration {i} of {self._num_of_iters}\r")
            self.current_iter += 1
        self.game.database.db_conn.commit()

    def _step(self):
        raise NotImplementedError

    def print_results(self):
        raise NotImplementedError


class SimFirstPositionSimpleFull(SYNSimulation):
    """Class for populating a database with 1st position simple runs at different table sizes"""

    def __init__(self, table_sz, lowest_to_keep, num_of_iters=DEFAULT_ITERS, dbname=DEFAULT_DB_NAME):
        """
        Sets up the sim using the lowest value that hero will keep, and the max table size.
        Sim will run an even amount of runs at each table size ranging from 2 to n, where n is
        the table_sz parameter here.

        Arguments:
            table_sz {int} -- max table size
            lowest_to_keep {Rank.value (int)} -- attempt to swap any card rank lower than this

        Keyword Arguments:
            dbname {str} -- [description] (default: {'SYNDB.db'})
        """

        if table_sz < 2:
            raise Exception("Table must be 2 or more seats")
        if lowest_to_keep > Rank.King or lowest_to_keep < Rank.Ace:
            raise Exception("Lowest card rank is not a card rank")
        super().__init__("Sim_1st_position_simple_full_spectrum", dbname, table_sz, num_of_iters)
        self.lowest_to_keep = lowest_to_keep
        self.current_villain_seat = 1
        self.current_iter = 1
        self.iters_per_count = int(self._num_of_iters / (table_sz - 1))
        # add hero
        heroname = FIRSTPOS_SIMPLE_NAME + str(self.lowest_to_keep)
        self.hero = SYNPlayer(SYNStrat_naive_firstonly(self.lowest_to_keep), heroname, self.game)
        self.game.state.add_player(self.hero, 0)
        # add first villain, more will be added later
        villainname = "cheater_villain" + str(self.current_villain_seat)
        villain = SYNPlayer(SYNStrat_cheater_villain(), villainname, self.game)
        self.game.state.add_player(villain, self.current_villain_seat)
        # move button to last pos, making 0th pos UTG
        self.game.state.dealer_button = self.current_villain_seat
        logging.basicConfig(level=logging.INFO, filename="fullspec.log", filemode='w')

    def _step(self):
        """
        If this iteration is a multiple of the iters per player count (and we're not done), add a player
        Then play a round
        """
        if (self.current_iter % self.iters_per_count == 0) and (len(self.game.state.table.seats) > (self.current_villain_seat + 1)):
            self.current_villain_seat += 1
            villainname = "cheater_villain" + str(self.current_villain_seat)
            villain = SYNPlayer(SYNStrat_cheater_villain(), villainname, self.game)
            self.game.state.add_player(villain, self.current_villain_seat)
            self.game.state.dealer_button = self.current_villain_seat
            logging.info(f"Added villain in seat {self.current_villain_seat}")
        self.game.play_a_round(practice_round=True)

    def print_results(self):
        """
        Prints a message instructing to get some results using a results command
        """
        print("Database populated with simulated runs.  Get results using a results command.")


def run_first_pos_full_default():
    for lowest in range(1, 14):
        print(f"Running full spectrum sim with 10 tablesize, keeping {lowest} and above")
        sim = SimFirstPositionSimpleFull(10, Rank(lowest), num_of_iters=DEFAULT_ITERS, dbname=DEFAULT_DB_NAME)
        sim.run(consoleprint=True)
        sim.print_results()


if __name__ == "__main__":
    """Command line script"""
    parser = ArgumentParser(description='Run one of a number of SYN sims')
    parser.add_argument('sim', choices=['simplefirst', 'get_simplefirst_winrate', 'full_spectrum_first'], nargs='?', default='full_spectrum_first')
    parser.add_argument('-r', '--runs', type=int, default=DEFAULT_ITERS)
    parser.add_argument('--db', default=DEFAULT_DB_NAME)
    parser.add_argument('-p', '--players', type=int, default=10)
    parser.add_argument('-l', '--low_to_keep', type=int, default=5, help='Lowest rank card to keep')
    parser.add_argument('--swap', type=lambda x: bool(util.strtobool(x)), default='True', help='Used when getting winrates')
    args = parser.parse_args()

    if args.sim == 'get_simplefirst_winrate':
        database = DBInterface(args.db)
        winratio = database.get_win_ratio_when_acting_first(args.players, args.low_to_keep, args.swap)
        winpct = winratio * 100
        print(f'Win percent: {winpct}%')
    elif args.sim == 'full_spectrum_first':
        for lowest in range(1, 14):
            print(f"Running full spectrum sim with {args.players} tablesize, keeping {lowest} and above")
            sim = SimFirstPositionSimpleFull(args.players, Rank(lowest), args.runs, dbname=args.db)
            sim.run(consoleprint=True)
            sim.print_results()
    else:
        print(f"{args.sim} is not a valid simulation.")
