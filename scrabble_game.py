'''
scrabble_game.py -- contains classes that model scrabble moves
'''
import collections
import operator
import random

import config
import scrabble_board

def decrement_letter(character):
    return chr(ord(character) - 1)

def increment_letter(character):
    return chr(ord(character) + 1)

def is_sublist(list_1, list_2):
    counter_1 = collections.Counter(list_1)
    counter_2 = collections.Counter(list_2)
    for value, cardinality in counter_1.items():
        if cardinality > counter_2[value]:
            return False

    return True


class ScrabbleGame(object):
    def __init__(self, num_players):
        self.num_players = num_players
        self.tile_bag = self.initialize_tile_bag()
        self.player_rack_list = self.initialize_player_racks()
        self.board = scrabble_board.ScrabbleBoard()
        self.player_move_score_list_list = [[] for _ in range(num_players)]
        self.move_number = 0

    def __repr__(self):
        player_str_list = []

        for i in range(self.num_players):
            player_str_list.append(
                'Player {player_number}: {score}'.format(
                    player_number=(i + 1),
                    score=sum(self.player_move_score_list_list[i])
                )
            )

        player_str = '\n'.join(player_str_list)

        return (
            '{board}\n'
            '{player_rack_list}\n'
            'Moves played: {move_number}\n'
            'Player {player_to_move}\'s move\n'
            '{tiles_remaining} tiles remain in bag\n'
            '{player_str}'
        ).format(
            board=str(self.board),
            player_rack_list=self.player_rack_list,
            move_number=self.move_number,
            player_to_move=(self.move_number % self.num_players) + 1,
            tiles_remaining=len(self.tile_bag),
            player_str=player_str,
        )

    def conclude_game(self, empty_rack_player_id=None):
        all_rack_points = 0

        for i, player_rack in enumerate(self.player_rack_list):
            rack_point_total = sum((tile.point_value for tile in player_rack))
            self.player_move_score_list_list[i].append(-1 * rack_point_total)
            all_rack_points += rack_point_total

        if empty_rack_player_id:
            self.player_move_score_list_list[empty_rack_player_id].append(
                all_rack_points
            )

        player_score_total_list = [
            sum(player_move_score_list)
            for player_move_score_list in self.player_move_score_list_list
        ]

        winning_player_id, winning_player_score = max(
            enumerate(player_score_total_list), key=operator.itemgetter(1)
        )

        print(
            'Game Over! Player {} wins with a score of {}'.format(
                winning_player_id + 1,
                winning_player_score
            )
        )

    @staticmethod
    def get_next_location_function(use_positive_seek, use_vertical_words):
        if use_vertical_words and use_positive_seek:
            return lambda (x, y): (x, y + 1)
        elif use_vertical_words and not use_positive_seek:
            return lambda (x, y): (x, y - 1)
        elif not use_vertical_words and use_positive_seek:
            return lambda (x, y): (increment_letter(x), y)
        elif not use_vertical_words and not use_positive_seek:
            return lambda (x, y): (decrement_letter(x), y)
        else:
            raise ValueError('Incorrect input.')

    def get_word_location_set(self, location, use_vertical_words):
        word_location_set = set([])

        for use_positive_seek in [True, False]:
            current_location = location
            current_tile = self.board[current_location].tile

            next_location_function = self.get_next_location_function(
                use_positive_seek,
                use_vertical_words
            )

            while current_tile:
                word_location_set.add(current_location)
                current_location = next_location_function(current_location)

                if (ord(current_location[0]) >= ord('a') and  # bounds check
                        ord(current_location[0]) <= ord('o') and
                        current_location[1] >= 1 and
                        current_location[1] <= 15):
                    current_tile = self.board[current_location].tile
                else:
                    current_tile = None

        if len(word_location_set) > 1:
            return frozenset(word_location_set)
        else:
            return None

    def get_word_set(self, move_location_set):
        word_set = set([])

        for use_vertical_words in [True, False]:
            for location in move_location_set:
                word_set.add(
                    self.get_word_location_set(
                        location,
                        use_vertical_words=use_vertical_words
                    )
                )

        return word_set

    def get_word_set_total_score(self, word_set, num_move_locations):
        total_score = 0
        word_score = 0

        for word_location_set in word_set:
            word_score = 0
            word_multiplier = 1

            for location in word_location_set:
                square = self.board[location]
                word_multiplier *= square.word_multiplier
                word_score += square.tile.point_value * square.letter_multiplier
                square.letter_multiplier = 1
                square.word_multiplier = 1

            word_score *= word_multiplier

        total_score += word_score

        if num_move_locations == 7:
            total_score += 50  # Bingo

        return total_score

    def score_move(self, letter_location_set):
        move_location_set = set(
            (location for _, location in letter_location_set)
        )

        word_set = self.get_word_set(move_location_set)
        total_score = self.get_word_set_total_score(word_set,
                                                    len(move_location_set))

        return total_score

    @staticmethod
    def get_adjacent_location_set(location):
        column, row = location

        adjacent_location_set = set(
            [
                (increment_letter(column), row),
                (decrement_letter(column), row),
                (column, row + 1),
                (column, row - 1)
            ]
        )
        # Board boundary check
        remove_location_set = set(
            (
                (column, row) for column, row in adjacent_location_set
                if (row > 15 or
                    row < 1 or
                    ord(column) > ord('o') or
                    ord(column) < ord('a'))
            )
        )

        return adjacent_location_set - remove_location_set

    def location_touches_tile(self, location, new_tile_location_set):
        adjacent_location_set = self.get_adjacent_location_set(location)

        for adjacent_location in adjacent_location_set:
            adjacent_tile = self.board[adjacent_location].tile
            if adjacent_tile or (adjacent_location in new_tile_location_set):
                return True

        return False

    def move_touches_tile(self, location_set):
        if self.move_number == 0:
            if config.START_SQUARE not in location_set:
                return False
        else:
            new_tile_location_set = set([])
            for this_location in location_set:
                if not self.location_touches_tile(this_location,
                                                  new_tile_location_set):
                    return False
                else:
                    new_tile_location_set.add(this_location)

        return True

    def move_is_legal(self, letter_location_set, player_rack):
        player_rack_letter_list = [tile.letter for tile in player_rack]
        letter_list = [letter for letter, _ in letter_location_set]
        location_set = set((location for _, location in letter_location_set))

        # Bounds check
        for column, row in location_set:
            if (ord(column) < ord('a') or
                    ord(column) > ord('o') or
                    row < 1 or
                    row > 15):
                return False

        # Cannot stack tiles
        if len(letter_list) != len(location_set):
            return False

        # All tiles places are in one row or one column
        column_list = [location[0] for location in location_set]
        row_list = [location[1] for location in location_set]

        if len(set(column_list)) == 1:
            is_vertical_move = True
        elif len(set(row_list)) == 1:
            is_vertical_move = False
        else:
            return False

        # All tiles must be connected
        if is_vertical_move:
            this_column = letter_location_set[0][1][0]
            for this_row in range(min(row_list), max(row_list) + 1):
                this_tile = self.board[(this_column, this_row)].tile
                if not (this_tile or (this_column, this_row) in location_set):
                    return False
        else:
            this_row = letter_location_set[0][1][1]
            for this_column_num in range(ord(min(column_list)),
                                         ord(max(column_list)) + 1):
                this_column = chr(this_column_num)
                this_tile = self.board[(this_column, this_row)].tile
                if not (this_tile or (this_column, this_row) in location_set):
                    return False

        # Move does not cover any other tiles
        for location in location_set:
            if self.board[location].tile:
                return False
        # Move touches existing tile
        if not self.move_touches_tile(location_set):
            return False
        # Player is playing tiles that exist in player's rack
        if not is_sublist(letter_list, player_rack_letter_list):
            return False

        return True

    def next_player_move(self, letter_location_set):
        player_to_move = self.move_number % self.num_players
        player_rack = self.player_rack_list[player_to_move]

        if self.move_is_legal(letter_location_set, player_rack):
            for move_letter, board_location in letter_location_set:
                tile_index = self.get_rack_tile_index(player_rack, move_letter)
                self.place_tile(player_rack, tile_index, board_location)

            while len(player_rack) < 7:
                if self.tile_bag:
                    player_rack.append(self.draw_random_tile())
                else:
                    break

            move_score = self.score_move(letter_location_set)
            self.player_move_score_list_list[player_to_move].append(move_score)
            self.move_number += 1
            success = True

            if len(player_rack) == 0 and len(self.tile_bag) == 0:
                self.conclude_game(player_to_move)
        else:
            success = False

        return success

    def next_player_exchange(self, letter_list):
        if len(self.tile_bag) < 7 or len(letter_list) > 7:
            return False

        player_to_move = self.move_number % self.num_players
        player_rack = self.player_rack_list[player_to_move]

        exchange_tile_list = []
        for letter in letter_list:
            for tile in player_rack:
                if tile.letter == letter:
                    exchange_tile_list.append(tile)

        for _ in range(len(letter_list)):
            player_rack.append(self.draw_random_tile())

        for tile in exchange_tile_list:
            if tile not in player_rack:
                return False
            else:
                player_rack.remove(tile)

        self.tile_bag.extend(exchange_tile_list)
        self.move_number += 1

        return True

    @staticmethod
    def get_rack_tile_index(player_rack, move_letter):
        for i, rack_tile in enumerate(player_rack):
            if rack_tile.letter == move_letter:
                return i

        return None

    def place_tile(self, player_rack, rack_tile_index, board_location):
        ''' Takes format of rack_tile_index, board_location '''
        tile = player_rack.pop(rack_tile_index)
        self.board[board_location].tile = tile

    def draw_random_tile(self):
        random_index = random.randrange(0, len(self.tile_bag))
        return self.tile_bag.pop(random_index)

    def initialize_player_racks(self):
        player_rack_list = []
        for _ in range(self.num_players):
            this_rack = [self.draw_random_tile() for _ in range(7)]
            player_rack_list.append(this_rack)

        return player_rack_list

    @staticmethod
    def initialize_tile_bag():
        tile_bag = []
        for letter, magnitude in config.LETTER_DISTRIBUTION_DICT.items():
            for _ in range(magnitude):
                tile_bag.append(
                    scrabble_board.ScrabbleTile(
                        letter=letter,
                        point_value=config.LETTER_POINT_VALUES_DICT[letter]
                    )
                )

        return tile_bag
