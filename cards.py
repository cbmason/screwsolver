#!/usr/bin/env python

"""
cards.py

Implementation of a standard deck of playing cards.  Aces low.
"""

from collections import deque
from enum import Enum

import random


class Rank(Enum):
    Ace = 1
    Two = 2
    Three = 3
    Four = 4
    Five = 5
    Six = 6
    Seven = 7
    Eight = 8
    Nine = 9
    Ten = 10
    Jack = 11
    Queen = 12
    King = 13

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class Suit(Enum):
    Clubs = 1
    Diamonds = 2
    Hearts = 3
    Spades = 4


class Card:
    """Playing card class"""

    def __init__(self, suit, rank):
        """Create a card of given suit / rank

        Arguments:
            suit {Suit} -- Clubs through Spades
            rank {Rank} -- Ace through King
        """
        if type(suit) is not Suit:
            raise TypeError()
        if type(rank) is not Rank:
            raise TypeError()
        self.suit = suit
        self.rank = rank

    def is_stealable(self):
        return self.rank != Rank.King

    def __str__(self):
        return f"{self.rank.name} of {self.suit.name}"

    def __eq__(self, value):
        return (self.suit == value.suit) and (self.rank == value.rank)


# TODO: make a discard pile
class Deck:
    """Deck of cards"""

    def __init__(self, empty=False):
        """Create 1 full deck of cards

        Keyword Arguments:
            empty {bool} -- if True, make an empty deck instead of a full one (default: {False})
        """
        self.cards = deque([])
        if not empty:
            for suit in Suit:
                for rank in Rank:
                    self.cards.append(Card(suit, rank))

    def shuffle(self):
        random.shuffle(self.cards)

    def deal_single(self):
        """Draw one card from the top of the deck"""
        return self.cards.popleft()

    def deal_specific(self, suit, rank):
        """Draw a specific card from the deck"""
        try:
            self.cards.remove(Card(suit, rank))
            # if the remove didn't except, it was successful, so return the
            # card
            return Card(suit, rank)
        except Exception:
            return None

    def deal(self, players=1, handsize=1):
        """Deals <handsize> cards to <players> players

        Keyword Arguments:
            players {int} -- players to deal to (default: {1})
            handsize {int} -- Number of cards to deal (default: {1})
        """
        if (players * handsize) > len(self.cards):
            raise ValueError(f"Not enough cards in deck to deal {handsize} \
                cards to {players} players")
        # create hands
        hands = []
        for i in range(players):
            if self.nodeque:
                hands.append([])
            else:
                hands.append(deque([]))
        # deal
        for i in range(handsize):
            for hand in hands:
                card = self.deal_single()
                hand.append(card)
        return hands

    def return_card(self, card):
        """Put card on bottom of deck.  If card already exists in deck, throw error

        Arguments:
            card {Card} -- Card to put on bottom of deck
        """
        if card in self.cards:
            raise ValueError("Card already exists in deck!")
        self.cards.append(card)
