#!/usr/bin/env python

"""
screw_your_neighbor.py

Contains classes that implement the game state of Screw Your Neighbor
https://wizardofodds.com/games/screw-your-neighbor/
Kings are turned up only when attempting to steal, not automatically at start
"""

from cards import Deck, Rank
from database import DBInterface


class SYNTable:
    """Seats are indexed from 0"""

    def __init__(self, num_seats=2):
        """Create a table for the game"""
        self.num_seats = num_seats
        self.num_players = 0
        self.seats = [None] * num_seats
        self.players = []

    def add_player(self, player, seat):
        """Seat a player at the given seat.  Seats are indexed from 0

        If the seat is currently occupied, replace the player, and print a warning.

        Arguments:
            player {SYNPlayer} -- Player to seat
            seat {int} -- seat to take
        """
        if type(player) is not SYNPlayer:
            raise Exception(f'{player} is not a valid player')
        if seat >= len(self.seats):
            raise Exception(f'{seat} does not exist, table size is {len(self.seats)}')
        if self.seats[seat] is not None:
            # TODO: better logging
            print(f'{player} kicking {self.seats[seat]} out of seat {seat}')
        self.seats[seat] = player
        self.players = [person for person in self.seats if person is not None]
        self.num_players = len(self.players)


class SYNGame:
    """Class representing a game, composed of a name, gamestate and database"""

    def __init__(self, name, dbname, num_seats=2):
        """Constructor requires a database name"""
        i = 0
        realname = name
        if dbname is not None:
            self.database = DBInterface(dbname)
            self.id = self.database.get_new_game_id()
            while not self.database.check_game_name(realname):
                i += 1
                realname = name + str(i)
            self.database.enter_new_game(self.id, realname)
        self.name = realname
        self.state = SYNGameState(num_seats)

    def play_a_round(self, practice_round=False):
        """Play a round, add results to database if exists, then advance round"""
        self.state.start_round()
        self.state.process_turns()
        lowcard, self.state.cur_losers = self.state.calculate_results(practice_round)
        if self.database is not None:
            self.database.add_round_results(self)
        self.state.collect_all_hands()
        self.state.advance_round(practice_round)


class SYNGameState:
    """Game state class"""
    # TODO: visible vs nonvisible cards

    def __init__(self, num_seats=2, dbinterface=None):
        """Initialize with table size and database to use

        Keyword Arguments:
            number_of_seats {int} -- Size of the table we're playing at (default: {2})
        """
        # table is an array of SYNPlayers
        self.table = SYNTable(num_seats)
        # How many hands have been played
        self.round = 0
        self.dealer_button = 0
        self.deck = Deck()
        self.current_low = Rank.King
        self.cur_losers = []
        self.round = 0

    def add_player(self, player, seat):
        """Seat a player at the given seat.

        If the seat is currently occupied, replace the player, and print a warning.

        Arguments:
            player {SYNPlayer} -- Player to seat
            seat {int} -- seat to take
        """
        self.table.add_player(player, seat)
        player.join_game(self)

    def start_round(self):
        """Signal to every player to begin their turn"""
        # only deal a round if we have a full deck
        assert len(self.deck.cards) == 52
        self.cur_losers = []
        self.current_low = Rank.King
        # SHUFFLE UP AND DEAL
        self.deck.shuffle()
        for player in self.table.players:
            player.begin_turn()
        # Calculate current low (needed for Cheaters)
        for player in self.table.players:
            if player.current_card.rank < self.current_low:
                # new current low, clear the losers list and append this player
                self.current_low = player.current_card.rank

    def collect_all_hands(self):
        """Discard all players' hands back into the deck"""
        for player in self.table.players:
            if type(player) is SYNPlayer and player.current_card is not None:
                player.discard(self.deck)

    def process_turns(self):
        """Iterate over each player, and retrieve / perform their requested action"""
        num_players = len(self.table.players)
        if num_players < 2:
            raise ValueError("Need more than 1 player to play")
        first_player = self.dealer_button
        for i in range(num_players):
            # start with the player to the right of the dealer
            cur_seat = (first_player + i + 1) % num_players
            next_seat = (cur_seat + 1) % num_players
            cur_player = self.table.players[cur_seat]
            next_player = self.table.players[next_seat]
            swap = cur_player.take_turn()
            if swap:
                # Attempt swap, either with deck or player
                if cur_seat == self.dealer_button:
                    cur_player.draw(self.deck, replace=True)
                elif next_player.can_be_stolen_from():
                    SYNPlayer.swap(cur_player, next_player)

    def calculate_results(self, practice_round=False):
        """Return the lowest card, and the losers that had the card.  If not practice round,
           subtract money and determine if there's a winner"""
        self.current_low = Rank.King
        # Find the player(s) with the lowest card, remove money if not practice round
        for player in self.table.players:
            if player.current_card.rank == self.current_low:
                # tied for current low, add to the losers list
                self.cur_losers.append(player)
            elif player.current_card.rank < self.current_low:
                # new current low, clear the losers list and append this player
                self.current_low = player.current_card.rank
                self.cur_losers = [player]
        if practice_round is False:
            tiegame = True
            if self.cur_losers == self.table.players:
                for player in self.cur_losers:
                    if player.current_stack != 0:
                        tiegame = False
                        break
            if not tiegame:
                for player in self.cur_losers:
                    player.current_stack -= 1
        # return the card and the players that have it
        return self.current_low, self.cur_losers

    def advance_round(self, practice_round=False):
        """Increment round counter and move dealer button (if real game)"""
        self.round += 1
        if not practice_round:
            self.dealer_button = (self.dealer_button + 1) % len(self.table.players)


class SYNPlayer:
    """Class representing a player"""
    def __init__(self, strategy, name="dummy", game=None):
        """Initialize player with strategy they use, their name, and the game they're playing in"""
        self.playerID = 0
        self.current_stack = None
        self.orig_card = None
        self.pre_swap_card = None
        self.current_card = None
        self.name = name
        self.strategy = strategy
        self.attempted_to_swap = False
        self.target_of_swap = False
        self._game = game

    def draw(self, deck, replace=False):
        """
        Draw a card from a deck.  If we already have a card, replace it if flag is True

        Arguments:
            deck {Deck} -- deck to draw from
        """
        if self.current_card is None:
            self.current_card = deck.deal_single()
            self.orig_card = self.current_card
        elif replace:
            self.discard(deck)
            self.current_card = deck.deal_single()

    def draw_specific(self, deck, suit, rank):
        """Draw a specific card"""
        if self.current_card is not None:
            self.discard(deck)
        self.current_card = deck.deal_specific(suit, rank)

    def discard(self, deck):
        """
        Put a card back in the deck if we have one.  Return True if a card was
        discarded

        Arguments:
            deck {Deck} -- deck to return card to
        """
        if self.current_card is None:
            return False
        else:
            deck.return_card(self.current_card)
            self.current_card = None
            return True

    def begin_turn(self):
        """Initialize player variables, draw a card"""
        self.orig_card = None
        self.current_card = None
        self.attempted_to_swap = False
        self.target_of_swap = False
        self.draw(self._game.deck)

    def take_turn(self):
        """
        Run this player's strategy to determine whether to HOLD or SWAP.

        Returns True if we want to SWAP
        """
        self.attempted_to_swap = self.strategy.run(self, self._game)
        self.pre_swap_card = self.current_card
        return(self.attempted_to_swap)

    def join_game(self, game, stack=4):
        self._game = game
        self.current_stack = stack

    def leave_game(self):
        self._game = None

    def can_be_stolen_from(self):
        """Returns True if this player can be stolen from, False otherwise"""
        return(self.current_card.is_stealable())

    def get_relative_pos(self):
        """Position relative to button where button is the last position.  In other words: player order of action"""
        my_pos = self._game.table.players.index(self)
        players_cnt = self._game.table.num_players
        rel_pos = (my_pos - 1 - self._game.dealer_button) % players_cnt
        # always return in positive format
        if rel_pos < 0:
            rel_pos = players_cnt + rel_pos
        return(rel_pos)

    @staticmethod
    def swap(player1, player2):
        """Perform a cardswpa between two players.  Assumes that the swap is allowed, does not check validity"""
        temp = player1.current_card
        player1.current_card = player2.current_card
        player2.current_card = temp
        player2.target_of_swap = True
