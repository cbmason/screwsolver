#!/usr/bin/env python

"""
strategies.py

Interface / implementations for player strategies for playing
Screw Your Neighbor.  Every strategy must return True or False,
where True means "swap with neighbor if able"
"""

from cards import Rank


class SYNStrat():
    """Abstract class for SYN strategy."""

    def run(self, player, gamestate):
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError


class SYNStrat_cheater_villain(SYNStrat):
    """Generic villain that always makes the ideal play"""

    def run(self, player, gamestate):
        """
        Run 'ideal' strategy

        If on the button, just compares with pre-calculated min card rank in
        gamestate, and draws if we're <= to that rank.
        If not on the button, only swaps if we are lower than everyone else.
        """

        for opponent in gamestate.table.players:
            if opponent is not player:
                if opponent.current_card.rank < player.current_card.rank:
                    return False
        return True

    def __str__(self):
        return("Cheater Villain")


class SYNStrat_naive_firstonly(SYNStrat):
    """Simple first to act player strategy, keep if card is >= lowest to keep"""

    def __init__(self, lowest_to_keep=Rank(5)):
        """Constructor taking the lowest we're keeping"""
        self.lowest_to_keep = lowest_to_keep.value

    def run(self, player, gamestate):
        myseat = player.get_relative_pos()
        if myseat == 0:
            # we are first position, execute first pos decision
            return naive_pass_if_low(player, self.lowest_to_keep)
        else:
            raise NotImplementedError("This strategy is only for under the gun")

    def __str__(self):
        return(f"Naive First Position {self.lowest_to_keep}")


def always_stay(gamestate):
    return True


def naive_pass_if_low(player, lowest_to_keep):
    """Strategy logic: simply keeps if >= lowest

    Arguments:
        player -- self-reference to the player using the strategy
        lowest_to_keep {int} -- lowest
    """
    if player.current_card.rank.value >= lowest_to_keep:
        return False
    else:
        return True
