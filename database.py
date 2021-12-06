#!/usr/bin/env python

"""
database.py

Class that implements the sqlite3 database interface for screw your neighbor
history
"""

# from screw_your_neighbor import SYNPlayer

import sqlite3


class DBInterface:
    """Database interface"""

    """ Create Commands """

    # Player / game names are unique so they can be searched without knowing rowID

    CREATE_SYNGAME_TABLE = '''CREATE TABLE IF NOT EXISTS SYNGame (
            id                  integer PRIMARY KEY NOT NULL UNIQUE,
            name                text NOT NULL UNIQUE
            );
            '''

    CREATE_PLAYER_TABLE = '''CREATE TABLE IF NOT EXISTS Player (
            id                  integer PRIMARY KEY NOT NULL UNIQUE,
            name                text NOT NULL UNIQUE
            );
            '''

    CREATE_SYNROUND_TABLE = '''CREATE TABLE IF NOT EXISTS SYNRound (
            id                  integer PRIMARY KEY NOT NULL UNIQUE,
            game_id             integer NOT NULL,
            round_num           integer NOT NULL,
            num_players         integer NOT NULL,
            UNIQUE(game_id, round_num),
            FOREIGN KEY(game_id) REFERENCES SYNGame(id)
            );
            '''

    CREATE_SYNPLAYERENDSTATE_TABLE = '''CREATE TABLE IF NOT EXISTS SYNPlayerEndState (
            id                  integer PRIMARY KEY NOT NULL UNIQUE,
            player_id           integer NOT NULL,
            round_id            integer NOT NULL,
            position            integer NOT NULL,
            initial_card_rank   integer NOT NULL,
            pre_swap_card_rank  integer NOT NULL,
            final_card_rank     integer NOT NULL,
            strategy            text NOT NULL,
            attempted_swap      integer,
            target_of_swap      integer,
            lost_round          integer NOT NULL,
            FOREIGN KEY(player_id) REFERENCES Player(id),
            FOREIGN KEY(round_id) REFERENCES SYNRound(id)
            );
            '''

    """ Read commands """

    GET_NEW_GAME_ID_cmd = '''SELECT IFNULL(MAX(id), 0) + 1 FROM SYNGame'''

    """ Update commands """

    ADD_GAME_cmd = '''INSERT OR REPLACE INTO SYNGame
            (id, name)
            VALUES (?, ?)
            '''

    ADD_PLAYER_cmd = '''INSERT OR REPLACE INTO Player
            (name)
            VALUES (?)
            '''

    ADD_ROUND_cmd = '''INSERT OR REPLACE INTO SYNRound
            (game_id, round_num, num_players)
            VALUES (?, ?, ?)
            '''

    ADD_SYNPLAYERSTATE_cmd = '''INSERT OR REPLACE INTO SYNPlayerEndState
            (player_id, game_id, round_num, position, initial_card_rank,
            final_card_rank, strategy, attempted_swap, target_of_swap)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''

    def __init__(self, db_name):
        self.db_conn = sqlite3.connect(db_name)
        self.db_cursor = self.db_conn.cursor()
        self.db_cursor.row_factory = sqlite3.Row
        self.create_tables()

    def __exit__(self, exception_type, exception_value, traceback):
        self.db_conn.close()

    def __del__(self):
        self.db_conn.close()

    def create_tables(self):
        self.db_cursor.execute(self.CREATE_SYNGAME_TABLE)
        self.db_cursor.execute(self.CREATE_PLAYER_TABLE)
        self.db_cursor.execute(self.CREATE_SYNROUND_TABLE)
        self.db_cursor.execute(self.CREATE_SYNPLAYERENDSTATE_TABLE)

    def add_round_results(self, game):
        """Input the results of a round into all tables

        Arguments:
            game {SYNGame} -- The game this round is part of
        """
        # add game# if not there
        self.db_cursor.execute('SELECT id FROM SYNGame WHERE id=?', (game.id, ))
        game_id_fetch = self.db_cursor.fetchone()
        if game_id_fetch is None:
            self.db_cursor.execute('INSERT OR REPLACE INTO SYNGame (id, name) VALUES (?, ?)', (game.id, game.name))
            self.db_cursor.execute('SELECT id FROM SYNGame WHERE id=?', (game.id, ))
            game_id = self.db_cursor.fetchone()[0]
        else:
            game_id = game_id_fetch[0]

        # add round
        self.db_cursor.execute('INSERT OR REPLACE INTO SYNRound (game_id, round_num, num_players) VALUES (?, ?, ?)',
                               (game_id, game.state.round, game.state.table.num_players))
        round_id = self.db_cursor.lastrowid

        # add each player's state
        for player in game.state.table.players:
            self.db_cursor.execute('SELECT id FROM Player WHERE name=?', (player.name, ))
            player_id_fetch = self.db_cursor.fetchone()
            if player_id_fetch is None:
                self.db_cursor.execute('INSERT OR REPLACE INTO player (name) VALUES (?)', (player.name, ))
                self.db_cursor.execute('SELECT id FROM Player WHERE name=?', (player.name, ))
                player_id = self.db_cursor.fetchone()[0]
            else:
                player_id = player_id_fetch[0]
            loser = player in game.state.cur_losers
            self.db_cursor.execute('''INSERT INTO SYNPlayerEndState
                                    (player_id, round_id, position, initial_card_rank, pre_swap_card_rank,
                                    final_card_rank, strategy, attempted_swap, target_of_swap, lost_round)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (player_id, round_id, player.get_relative_pos(),
                                          player.orig_card.rank.value, player.pre_swap_card.rank.value,
                                          player.current_card.rank.value, str(player.strategy),
                                          player.attempted_to_swap, player.target_of_swap, loser))

    def get_new_game_id(self):
        """The query should always return 1 row, no need to check"""
        self.db_cursor.execute(self.GET_NEW_GAME_ID_cmd)
        return self.db_cursor.fetchone()[0]

    def enter_new_game(self, id, name):
        """Add a game"""
        self.db_cursor.execute("INSERT OR REPLACE INTO SYNGame (id, name) VALUES (?, ?)", (id, name))

    def check_game_name(self, name):
        """Returns True if the name is OK to use, False if it already exists in the DB"""
        self.db_cursor.execute('SELECT name FROM SYNGame WHERE name=?', (name,))
        exists = self.db_cursor.fetchone()
        if exists:
            return False
        else:
            return True

    def get_game_win_ratio(self, player_name, game_name):
        """Don't need to check each query, if they fail then we've recieved bad input, so just pass the exception up"""
        # get player id
        self.db_cursor.execute('''SELECT id FROM Player WHERE name=?''', (player_name,))
        player_id = self.db_cursor.fetchone()[0]
        # get game id
        self.db_cursor.execute('''SELECT id FROM SYNGame WHERE name=?''', (game_name,))
        game_id = self.db_cursor.fetchone()[0]
        # query num of rounds in game name
        self.db_cursor.execute('''SELECT COUNT(id) FROM SYNRound WHERE game_id=?''', (game_id,))
        total_cnt = self.db_cursor.fetchone()[0]
        self.db_cursor.execute('''SELECT COUNT(*) FROM SYNRound AS round
                JOIN SYNGame as games on rounds.game_id = games.id
                JOIN SYNPlayerEndState AS state ON round.id = state.round_id
                WHERE state.player_id=? AND games.id=? state.lost_round''', (player_id, game_id))
        loser_cnt = self.db_cursor.fetchone()[0]
        # divide
        if total_cnt != 0:
            retval = 1 - (loser_cnt / total_cnt)
        else:
            retval = 0
        return retval

    def get_win_ratio_when_acting_first(self, num_players=5, rankvalue=5, swap=True):
        """Given a playercount, and a starting card, and whether or not to swap, calculate winrate for 1st player"""
        self.db_cursor.execute('''SELECT COUNT(*) FROM SYNRound AS round
                JOIN SYNPlayerEndState AS state ON round.id = state.round_id
                WHERE state.position = 0 AND state.initial_card_rank = ? AND state.attempted_swap = ? AND round.num_players = ?''',
                               (rankvalue, swap, num_players))
        total_cnt = self.db_cursor.fetchone()[0]

        self.db_cursor.execute('''SELECT COUNT(*) FROM SYNRound AS round
                JOIN SYNPlayerEndState AS state ON round.id = state.round_id
                WHERE state.position = 0 AND state.initial_card_rank = ? AND state.attempted_swap = ? AND round.num_players = ? AND state.lost_round''',
                (rankvalue, swap, num_players))

        loser_cnt = self.db_cursor.fetchone()[0]
        if total_cnt != 0:
            retval = 1 - (loser_cnt / total_cnt)
        else:
            retval = 0
        print(f"When initial value is {rankvalue}, swap={swap}, and {num_players} players:")
        print(f"loser_cnt={loser_cnt}, total_cnt={total_cnt}")
        return retval

    def get_does_player_count_exist(self, player_count):
        """
        Query whether database contains games with the queried number of players.
        :param player_count:
        :return: TRUE if there are games logged with the queried count, FALSE otherwise
        """
        self.db_cursor.execute('''SELECT COUNT(*) FROM SYNRound WHERE num_players = ?''',
                               (player_count,))
        count = self.db_cursor.fetchone()[0]
        return count != 0
