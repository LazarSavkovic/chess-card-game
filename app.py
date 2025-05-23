from flask import Flask, render_template,  redirect
from flask_sock import Sock
import json
from cards import *
from card_types import Monster, Card
from random import shuffle, choice
from util import get_concrete_subclasses, get_playable_card_classes
import uuid
import time


app = Flask(__name__)
sock = Sock(app)


connected_users = {}
games = {}


class ChessGame:
    def __init__(self):
        self.board = self.init_board()
        self.land_board = self.init_land_board()
        self.players = ['1', '2']
        self.mana = {'1': 50, '2': 50}
        self.graveyard = {'1': [], '2': []}


        self.turn_index = 0
        self.moves_this_turn = 0
        self.max_moves_per_turn = 3
        self.center_tile_control = {
            '1': 0,
            '2': 0
        }

        all_card_classes = get_playable_card_classes()

        self.decks = {
            '1': [choice(all_card_classes)('1') for _ in range(40)],
            '2': [choice(all_card_classes)('2') for _ in range(40)]
        }

        shuffle(self.decks['1'])
        shuffle(self.decks['2'])

        # Initial hands = draw 3 cards from the deck
        self.hands = {
            '1': [self.decks['1'].pop() for _ in range(4)],
            '2': [self.decks['2'].pop() for _ in range(4)]
        }
        self.summoned_this_turn = set()
        self.sorcery_used_this_turn = set()
        self.land_placed_this_turn = set()

    @staticmethod
    def get_valid_summon_positions(user_id):
        r = 0 if user_id == '2' else 6
        return [[r, col] for col in [0, 3, 6]]

    def draw_card(self, user_id):
        if self.decks[user_id]:
            self.hands[user_id].append(self.decks[user_id].pop(0))

    def summon_card(self, slot_index, to_pos, user_id):
        if user_id != self.current_player:
            return False, "Not your turn"
        if user_id in self.summoned_this_turn:
            return False, "You've already summoned this turn"

        if to_pos not in self.get_valid_summon_positions(user_id):
            return False, "Invalid summon position"

        tx, ty = to_pos
        if self.board[tx][ty] is not None:
            return False, "Tile is occupied"

        hand = self.hands[user_id]
        if not (0 <= slot_index < len(hand)):
            return False, "Invalid card slot"

        card = hand.pop(slot_index)
        if self.mana[user_id] < card.mana:
            return False, "Not enough mana"
        self.mana[user_id] -= card.mana
        self.board[tx][ty] = card
        self.summoned_this_turn.add(user_id)
        return True, f"{card.name} summoned!"

    def init_board(self):
        board = [[None for _ in range(7)] for _ in range(7)]

        return board

    def init_land_board(self):
        land_board = [[None for _ in range(7)] for _ in range(7)]

        return land_board

    @property
    def current_player(self):
        return self.players[self.turn_index]

    def toggle_turn(self):
        # 👇 Initialize if missing
        if not hasattr(self, 'center_tile_control'):
            self.center_tile_control = {'1': 0, '2': 0}

        center_piece = self.board[3][3]
        if center_piece:
            owner = center_piece.owner
            other = '1' if owner == '2' else '2'

            self.center_tile_control[owner] += 1
            self.center_tile_control[other] = 0  # reset opponent's control
        else:
            # No one controls center
            self.center_tile_control['1'] = 0
            self.center_tile_control['2'] = 0

        self.turn_index = (self.turn_index + 1) % len(self.players)
        self.moves_this_turn = 0
        self.summoned_this_turn.clear()
        self.sorcery_used_this_turn.clear()
        self.land_placed_this_turn.clear()
        self.draw_card(self.current_player)

        for x in range(7):
            for y in range(7):
                card = self.board[x][y]
                land = self.land_board[x][y]
                if card and land and hasattr(land, 'on_turn_start'):
                    land.on_turn_start(self, (x, y), card)

    def can_move(self, user_id):
        return user_id == self.current_player and self.moves_this_turn < self.max_moves_per_turn

    def direct_attack(self, pos, user_id):
        if not self.can_move(user_id):
            return False, "You've used all your moves", False

        x, y = pos
        card = self.board[x][y]
        if not card or card.owner != user_id:
            return False, "Invalid card selected", False

        opponent = '2' if user_id == '1' else '1'
        back_row = 0 if user_id == '1' else 6
        if x != back_row:
            return False, "Not in position for direct attack", False

        self.mana[opponent] -= card.mana

        self.moves_this_turn += 1

        # Optional win check
        if self.mana[opponent] <= 0:
            self.mana[opponent] = 0
            return True, f"{card.name} dealt a final blow!", True

        return True, f"{card.name} attacked directly for {card.mana} mana!", False


    def move(self, from_pos, to_pos, user_id):
        if not self.can_move(user_id):
            return False, "You've used all your moves"

        fx, fy = from_pos
        tx, ty = to_pos
        card = self.board[fx][fy]

        if not card:
            return False, "No card at source"
        if card.owner != user_id:
            return False, "That's not your card"
        if not Monster.can_move(card, from_pos, to_pos, self.board):
            return False, "Invalid move"
        # Blocked path check (no jumping)
        dx = tx - fx
        dy = ty - fy
        step_x = 0 if dx == 0 else dx // abs(dx)
        step_y = 0 if dy == 0 else dy // abs(dy)

        x, y = fx + step_x, fy + step_y
        while (x, y) != (tx, ty):
            if self.board[x][y] is not None:
                return False, "Path blocked by another monster"
            x += step_x
            y += step_y
            land = self.land_board[x][y]
            if land:
                if hasattr(land, 'blocks_movement') and land.blocks_movement(card):
                    return False, f"{land.name} blocks movement!"

        target = self.board[tx][ty]
        target_land = self.land_board[tx][ty]
        if target_land:
            if hasattr(target_land, 'blocks_movement') and target_land.blocks_movement(card):
                return False, f"{target_land.name} blocks movement!"
            if hasattr(target_land, 'affects_monster_passing'):
                target_land.affects_monster_passing(card)
                return False, f"{target_land.name} blocks movement!"
            else:
                if hasattr(target_land, 'on_enter'):
                    target_land.on_enter(self, (tx, ty), card)

        if target:
            if target.owner == card.owner:
                return False, "Can't capture your own card"
            if card.attack > target.defense:
                self.graveyard[target.owner].append(target)
                self.board[tx][ty] = card
                self.board[fx][fy] = None
                self.moves_this_turn += 1
                return True, f"{card.name} defeated {target.name}!"
            if card.attack == target.defense:
                self.graveyard[target.owner].append(target)
                self.graveyard[card.owner].append(card)
                self.board[tx][ty] = None
                self.board[fx][fy] = None
                self.moves_this_turn += 1
                return True, f"{card.name} and {target.name} defeated!"
            else:
                self.graveyard[card.owner].append(card)
                self.board[fx][fy] = None
                self.moves_this_turn += 1
                return True, f"{card.name} was killed by {target.name}!"
        else:
            self.board[tx][ty] = card
            self.board[fx][fy] = None
            self.moves_this_turn += 1
            return True, "Move successful"

        self.board[tx][ty] = card
        self.board[fx][fy] = None
        self.moves_this_turn += 1
        return True, "Move successful"

    def game_can_activate_card(self,slot_index, user_id, target_pos):
        if user_id != self.current_player:
            return False, "Not your turn"

        if user_id in self.sorcery_used_this_turn:
            return False, "You've already used a sorcery this turn"

        hand = self.hands[user_id]
        if not (0 <= slot_index < len(hand)):
            return False, "Invalid card slot"

        card = hand[slot_index]
        if card.type != 'sorcery':
            return False, "This is not a sorcery"

        if self.mana[user_id] < card.mana:
            return False, "Not enough mana"

        if target_pos is None:
            return False, "No activation position provided"

        if not card.can_activate(self, target_pos[0], target_pos[1]):
            return False, "Activation needs not met"
        return True, 'Card can be activated'


    def activate_sorcery(self, slot_index, user_id, target_pos):
        hand = self.hands[user_id]
        card = hand[slot_index]

        self.mana[user_id] -= card.mana
        hand.pop(slot_index)
        self.graveyard[user_id].append(card)
        self.sorcery_used_this_turn.add(user_id)

        card.affect_board(self, tuple(target_pos), user_id)

        return True, f"{card.name} activated!"

    def game_can_place_land(self, slot_index, user_id, to_pos):
        if user_id != self.current_player:
            return False, "Not your turn"

        if user_id in self.land_placed_this_turn:
            return False, "You've already created a land this turn"

        hand = self.hands[user_id]
        if not (0 <= slot_index < len(hand)):
            return False, "Invalid card slot"

        card = hand[slot_index]
        if card.type != 'land':
            return False, "Not a land card"

        if self.mana[user_id] < card.mana:
            return False, "Not enough mana"

        x, y = to_pos
        if self.land_board[x][y] is not None:
            return False, "Land already exists here"

        x, y = to_pos
        if self.board[x][y] is not None:
            return False, "Tile is occupied"

        # Optional: Check card.creation_needs like sorceries do
        if hasattr(card, "creation_needs") and not card.can_create(self, x, y):
            return False, "Creation needs not met"

        return True, 'Land can be placed'


    def place_land(self, slot_index, user_id, to_pos):
        x, y = to_pos

        hand = self.hands[user_id]
        card = hand[slot_index]

        self.land_placed_this_turn.add(user_id)
        self.mana[user_id] -= card.mana
        hand.pop(slot_index)
        self.land_board[x][y] = card
        return True, f"{card.name} placed as land"


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create-room')
def create_room():
    room_id = str(uuid.uuid4())  # Generate a unique UUID
    return redirect(f'/room/{room_id}')  # Redirect to /room/{uuid}


@app.route('/room/<game_id>')
def room(game_id):
    return render_template('room.html')


@sock.route('/game/<game_id>')
def game(ws, game_id):
    if game_id not in games:
        games[game_id] = ChessGame()

    game = games[game_id]
    user_id = None

    try:
        while True:
            message = ws.receive()
            if not message:
                break

            data = json.loads(message)

            if not user_id:
                if game_id not in connected_users:
                    connected_users[game_id] = {}

                game_users = connected_users[game_id]

                if '1' not in game_users:
                    user_id = '1'
                elif '2' not in game_users:
                    user_id = '2'
                else:
                    ws.send(json.dumps({'type': 'error', 'message': 'Game room is full'}))
                    return

                game_users[user_id] = ws

                # 👇 Send the assigned user ID back to the client
                ws.send(json.dumps({'user_id': user_id}))

                serialized_board = [[p.to_dict() if p else None for p in row] for row in game.board]
                serialized_land_board = [[p.to_dict() if p else None for p in row] for row in game.land_board]
                hand1 = [c.to_dict() for c in game.hands['1']]
                hand2 = [c.to_dict() for c in game.hands['2']]

                # Send initial board + hands
                ws.send(json.dumps({
                    'type': 'init',
                    'board': serialized_board,
                    'land_board': serialized_land_board,
                    'hand1': [c.to_dict() for c in game.hands['1']],
                    'hand2': [c.to_dict() for c in game.hands['2']],
                    'turn': game.current_player,
                    'mana': game.mana,
                    'graveyard': {
                        '1': [c.to_dict() for c in game.graveyard['1']],
                        '2': [c.to_dict() for c in game.graveyard['2']],
                    },
                    'deck_sizes': {
                        '1': len(game.decks['1']),
                        '2': len(game.decks['2']),
                    },
                                'center_tile_control': game.center_tile_control


                }))


            elif data['type'] == 'move':
                from_pos = data['from']
                to_pos = data['to']
                success, info = game.move(from_pos, to_pos, user_id)
                serialized_board = [[p.to_dict() if p else None for p in row] for row in game.board]
                serialized_land_board = [[p.to_dict() if p else None for p in row] for row in game.land_board]

                if success:
                    for other_ws in connected_users[game_id].values():
                        other_ws.send(json.dumps({
                            'type': 'update',
                            'board': serialized_board,
                            'land_board': serialized_land_board,
                            'turn': game.current_player,
                            'success': success,
                            'hand1': [c.to_dict() for c in game.hands['1']],
                            'hand2': [c.to_dict() for c in game.hands['2']],
                            'info': info,
                            'from': from_pos,
                            'mana': game.mana,
                            'graveyard': {
                                '1': [c.to_dict() for c in game.graveyard['1']],
                                '2': [c.to_dict() for c in game.graveyard['2']],
                            },
                            'deck_sizes': {
                                '1': len(game.decks['1']),
                                '2': len(game.decks['2']),
                            },
                            'to': to_pos,
                            'user_id': user_id,
                            'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                                'center_tile_control': game.center_tile_control
                        }))
                else:
                    # Only notify the user who tried the move
                    ws.send(json.dumps({
                        'type': 'update',
                        'board': serialized_board,
                        'land_board': serialized_land_board,
                        'turn': game.current_player,
                        'success': success,
                        'info': info,
                        'hand1': [c.to_dict() for c in game.hands['1']],
                        'hand2': [c.to_dict() for c in game.hands['2']],
                        'from': from_pos,
                        'to': to_pos,
                        'mana': game.mana,
                        'graveyard': {
                            '1': [c.to_dict() for c in game.graveyard['1']],
                            '2': [c.to_dict() for c in game.graveyard['2']],
                        },
                            'deck_sizes': {
                                '1': len(game.decks['1']),
                                '2': len(game.decks['2']),
                            },
                        'user_id': user_id,
                        'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                                'center_tile_control': game.center_tile_control
                    }))
            elif (data['type'] == 'end-turn') or (data['type'] == 'end-turn-with-discard'):
                if data['type'] == 'end-turn-with-discard':

                    discarded_card = game.hands[user_id].pop(data['slot'])
                    game.graveyard[user_id].append(discarded_card)

                if len(game.hands[user_id]) > 5:

                    for uid, ws_conn in connected_users[game_id].items():
                        ws_conn.send(json.dumps({
                            'type': 'discard-to-end-turn' if uid == user_id else 'opponent-discarding',
                            'board': [[p.to_dict() if p else None for p in row] for row in game.board],
                            'land_board': [[p.to_dict() if p else None for p in row] for row in game.land_board],
                            'hand1': [c.to_dict() for c in game.hands['1']],
                            'hand2': [c.to_dict() for c in game.hands['2']],
                            'graveyard': {
                                '1': [c.to_dict() for c in game.graveyard['1']],
                                '2': [c.to_dict() for c in game.graveyard['2']],
                            },
                            'deck_sizes': {
                                '1': len(game.decks['1']),
                                '2': len(game.decks['2']),
                            },
                            'turn': game.current_player,
                            'success': True,
                            'mana': game.mana,
                            'info': f"Discarding needed to end turn!",
                            'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                            'center_tile_control': game.center_tile_control
                        }))

                elif game.center_tile_control[user_id] >= 6:
                    # This player wins
                    for uid, ws_conn in connected_users[game_id].items():
                        ws_conn.send(json.dumps({
                            'type': 'game-over',
                            'board': [[p.to_dict() if p else None for p in row] for row in game.board],
                            'land_board': [[p.to_dict() if p else None for p in row] for row in game.land_board],
                            'hand1': [c.to_dict() for c in game.hands['1']],
                            'hand2': [c.to_dict() for c in game.hands['2']],
                            'graveyard': {
                                '1': [c.to_dict() for c in game.graveyard['1']],
                                '2': [c.to_dict() for c in game.graveyard['2']],
                            },
                            'deck_sizes': {
                                '1': len(game.decks['1']),
                                '2': len(game.decks['2']),
                            },
                            'turn': game.current_player,
                            'success': True,
                            'mana': game.mana,
                            'info': f"Player {user_id} has controlled the center for 6 turns!",
                            'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                            'game_over': {
                                'result': 'victory' if uid == user_id else 'defeat'
                            },
                            'center_tile_control': game.center_tile_control
                        }))

                elif user_id == game.current_player:
                    game.toggle_turn()
                    serialized_board = [[p.to_dict() if p else None for p in row] for row in game.board]
                    serialized_land_board = [[p.to_dict() if p else None for p in row] for row in game.land_board]

                    for other_ws in connected_users[game_id].values():
                        other_ws.send(json.dumps({
                            'type': 'update',
                            'board': serialized_board,
                            'land_board': serialized_land_board,
                            'mana': game.mana,
                            'hand1': [c.to_dict() for c in game.hands['1']],
                            'hand2': [c.to_dict() for c in game.hands['2']],
                            'graveyard': {
                                '1': [c.to_dict() for c in game.graveyard['1']],
                                '2': [c.to_dict() for c in game.graveyard['2']],
                            },
                            'deck_sizes': {
                                    '1': len(game.decks['1']),
                                    '2': len(game.decks['2']),
                                },
                            'turn': game.current_player,
                            'info': f"Player {user_id} ended their turn.",
                            'success': True,
                            'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                            'center_tile_control': game.center_tile_control
                        }))

            elif data['type'] == 'summon':
                slot = data['slot']
                to_pos = data['to']
                success, info = game.summon_card(slot, to_pos, user_id)
                serialized_board = [[p.to_dict() if p else None for p in row] for row in game.board]
                serialized_land_board = [[p.to_dict() if p else None for p in row] for row in game.land_board]


                if success:
                    for ws_conn in connected_users[game_id].values():
                        ws_conn.send(json.dumps({
                            'type': 'update',
                            'board': serialized_board,
                            'land_board': serialized_land_board,
                            'hand1': [c.to_dict() for c in game.hands['1']],
                            'hand2': [c.to_dict() for c in game.hands['2']],
                            'turn': game.current_player,
                            'success': success,
                            'graveyard': {
                                '1': [c.to_dict() for c in game.graveyard['1']],
                                '2': [c.to_dict() for c in game.graveyard['2']],
                            },
                            'deck_sizes': {
                                '1': len(game.decks['1']),
                                '2': len(game.decks['2']),
                            },
                            'info': info,
                            'to': to_pos,
                            'mana': game.mana,
                            'center_tile_control': game.center_tile_control
                        }))
                else:
                    # Only notify the player who attempted the summon
                    connected_users[game_id][user_id].send(json.dumps({
                        'type': 'update',
                        'board': serialized_board,
                        'land_board': serialized_land_board,
                        'hand1': [c.to_dict() for c in game.hands['1']],
                        'hand2': [c.to_dict() for c in game.hands['2']],
                        'turn': game.current_player,
                        'success': success,
                        'graveyard': {
                            '1': [c.to_dict() for c in game.graveyard['1']],
                            '2': [c.to_dict() for c in game.graveyard['2']],
                        },
                        'deck_sizes': {
                            '1': len(game.decks['1']),
                            '2': len(game.decks['2']),
                        },
                        'info': info,
                        'to': to_pos,
                        'mana': game.mana,
                        'center_tile_control': game.center_tile_control
                    }))

            elif data['type'] == 'direct-attack':
                pos = data['pos']
                success, info, game_over = game.direct_attack(pos, user_id)
                serialized_board = [[p.to_dict() if p else None for p in row] for row in game.board]
                serialized_land_board = [[p.to_dict() if p else None for p in row] for row in game.land_board]

                if game_over:
                    winner = user_id
                    loser = '1' if user_id == '2' else '2'
                    for uid, ws_conn in connected_users[game_id].items():
                        ws_conn.send(json.dumps({
                            'type': 'game-over',
                            'board': serialized_board,
                            'land_board': serialized_land_board,
                            'hand1': [c.to_dict() for c in game.hands['1']],
                            'hand2': [c.to_dict() for c in game.hands['2']],
                            'graveyard': {
                                '1': [c.to_dict() for c in game.graveyard['1']],
                                '2': [c.to_dict() for c in game.graveyard['2']],
                            },
                            'deck_sizes': {
                                '1': len(game.decks['1']),
                                '2': len(game.decks['2']),
                            },
                            'turn': game.current_player,
                            'success': True,
                            'mana': game.mana,
                            'info': info,
                            'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                            'game_over': {
                                'result': 'victory' if uid == winner else 'defeat'
                            },
                            'center_tile_control': game.center_tile_control
                        }))
                    return
                else:
                    for other_ws in connected_users[game_id].values():
                        other_ws.send(json.dumps({
                            'type': 'update',
                            'board': serialized_board,
                            'land_board': serialized_land_board,
                            'hand1': [c.to_dict() for c in game.hands['1']],
                            'hand2': [c.to_dict() for c in game.hands['2']],
                            'graveyard': {
                                '1': [c.to_dict() for c in game.graveyard['1']],
                                '2': [c.to_dict() for c in game.graveyard['2']],
                            },
                            'deck_sizes': {
                                        '1': len(game.decks['1']),
                                        '2': len(game.decks['2']),
                                    },
                            'turn': game.current_player,
                            'success': success,
                            'mana': game.mana,
                            'info': info,
                            'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                            'center_tile_control': game.center_tile_control
                        }))

            elif data['type'] == 'activate-sorcery':
                if not user_id:
                    continue  # or raise, or wait — don't access hands/cards yet

                slot = data['slot']
                target = data.get('pos')  # optional
                card = game.hands[user_id][slot]
                success, info = game.game_can_activate_card(slot, user_id, target)
                if not success:

                    serialized_board = [[p.to_dict() if p else None for p in row] for row in game.board]
                    serialized_land_board = [[p.to_dict() if p else None for p in row] for row in game.land_board]
                    # Only notify the user who tried the move
                    ws.send(json.dumps({
                        'type': 'update',
                        'board': serialized_board,
                        'land_board': serialized_land_board,
                        'hand1': [c.to_dict() for c in game.hands['1']],
                        'hand2': [c.to_dict() for c in game.hands['2']],
                        'turn': game.current_player,
                        'success': success,
                        'graveyard': {
                            '1': [c.to_dict() for c in game.graveyard['1']],
                            '2': [c.to_dict() for c in game.graveyard['2']],
                        },
                        'mana': game.mana,
                        'info': info,
                        'deck_sizes': {
                            '1': len(game.decks['1']),
                            '2': len(game.decks['2']),
                        },
                        'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                        'center_tile_control': game.center_tile_control
                    }))
                else:

                    if callable(getattr(card, "requires_additional_input", None)) and card.requires_additional_input():

                        # 👇 Regular activate logic
                        success, info = True, f'{card.name} activated'
                        valid_targets = card.get_valid_targets(game, user_id)
                        serialized_board = [[p.to_dict() if p else None for p in row] for row in game.board]
                        serialized_land_board = [[p.to_dict() if p else None for p in row] for row in game.land_board]


                        connected_users[game_id][user_id].send(json.dumps({
                                'type': 'awaiting-input',
                                'board': serialized_board,
                                'land_board': serialized_land_board,
                                'hand1': [c.to_dict() for c in game.hands['1']],
                                'hand2': [c.to_dict() for c in game.hands['2']],
                                'turn': game.current_player,
                                'slot': slot,
                                'success': success,
                                'valid_targets': valid_targets,
                                'card_id': card.card_id,
                                'graveyard': {
                                    '1': [c.to_dict() for c in game.graveyard['1']],
                                    '2': [c.to_dict() for c in game.graveyard['2']],
                                },
                                'mana': game.mana,
                                'info': info,
                                'deck_sizes': {
                                    '1': len(game.decks['1']),
                                    '2': len(game.decks['2']),
                                },
                                'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                                'center_tile_control': game.center_tile_control
                            }))
                    else:
                        # 👇 Regular activate logic
                        success, info = game.activate_sorcery(slot, user_id, target)
                        serialized_board = [[p.to_dict() if p else None for p in row] for row in game.board]


                        for ws_conn in connected_users[game_id].values():
                            ws_conn.send(json.dumps({
                                'type': 'update',
                                'board': serialized_board,
                                'land_board': serialized_land_board,
                                'hand1': [c.to_dict() for c in game.hands['1']],
                                'hand2': [c.to_dict() for c in game.hands['2']],
                                'turn': game.current_player,
                                'success': success,
                                'graveyard': {
                                    '1': [c.to_dict() for c in game.graveyard['1']],
                                    '2': [c.to_dict() for c in game.graveyard['2']],
                                },
                                'mana': game.mana,
                                'info': info,
                                'deck_sizes': {
                                    '1': len(game.decks['1']),
                                    '2': len(game.decks['2']),
                                },
                                'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                                'center_tile_control': game.center_tile_control
                            }))

            elif data['type'] == 'resolve-sorcery':
                    slot = data['slot']
                    target = data['target']
                    card = game.hands[user_id][slot]

                    if hasattr(card, "resolve_with_input"):
                        # 👇 Try resolving first — don't remove card or spend mana yet
                        success, info = card.resolve_with_input(game, user_id, target)

                        if success:
                            game.hands[user_id].pop(slot)
                            game.graveyard[user_id].append(card)
                            game.mana[user_id] -= card.mana
                            game.sorcery_used_this_turn.add(user_id)

                        serialized_board = [[p.to_dict() if p else None for p in row] for row in game.board]
                        serialized_land_board = [[p.to_dict() if p else None for p in row] for row in game.land_board]

                        for ws_conn in connected_users[game_id].values():
                            ws_conn.send(json.dumps({
                                'type': 'update',
                                'board': serialized_board,
                                'land_board': serialized_land_board,
                                'hand1': [c.to_dict() for c in game.hands['1']],
                                'hand2': [c.to_dict() for c in game.hands['2']],
                                'turn': game.current_player,
                                'success': success,
                                'mana': game.mana,
                                'graveyard': {
                                    '1': [c.to_dict() for c in game.graveyard['1']],
                                    '2': [c.to_dict() for c in game.graveyard['2']],
                                },
                                'deck_sizes': {
                                    '1': len(game.decks['1']),
                                    '2': len(game.decks['2']),
                                },
                                'info': info,
                                'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                                'center_tile_control': game.center_tile_control

                            }))
            elif data['type'] == 'place-land':
                if not user_id:
                    continue  # or raise, or wait — don't access hands/cards yet

                slot = data['slot']
                target = data.get('pos')  # optional
                card = game.hands[user_id][slot]

                # 👇 Regular placement logic
                success, info = game.game_can_place_land(slot, user_id, target)
                if not success:
                    serialized_board = [[p.to_dict() if p else None for p in row] for row in game.board]
                    serialized_land_board = [[p.to_dict() if p else None for p in row] for row in game.land_board]

                    # Only notify the user who tried the move
                    ws.send(json.dumps({
                        'type': 'update',
                        'board': serialized_board,
                        'land_board': serialized_land_board,
                        'hand1': [c.to_dict() for c in game.hands['1']],
                        'hand2': [c.to_dict() for c in game.hands['2']],
                        'turn': game.current_player,
                        'success': success,
                        'graveyard': {
                            '1': [c.to_dict() for c in game.graveyard['1']],
                            '2': [c.to_dict() for c in game.graveyard['2']],
                        },
                        'mana': game.mana,
                        'info': info,
                        'deck_sizes': {
                            '1': len(game.decks['1']),
                            '2': len(game.decks['2']),
                        },
                        'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                        'center_tile_control': game.center_tile_control
                    }))
                else:


                    success, info = game.place_land(slot, user_id, target)
                    serialized_board = [[p.to_dict() if p else None for p in row] for row in game.board]
                    serialized_land_board = [[p.to_dict() if p else None for p in row] for row in game.land_board]

                    for ws_conn in connected_users[game_id].values():
                        ws_conn.send(json.dumps({
                            'type': 'update',
                            'board': serialized_board,
                            'land_board': serialized_land_board,
                            'hand1': [c.to_dict() for c in game.hands['1']],
                            'hand2': [c.to_dict() for c in game.hands['2']],
                            'turn': game.current_player,
                            'success': success,
                            'graveyard': {
                                '1': [c.to_dict() for c in game.graveyard['1']],
                                '2': [c.to_dict() for c in game.graveyard['2']],
                            },
                            'mana': game.mana,
                            'info': info,
                            'deck_sizes': {
                                '1': len(game.decks['1']),
                                '2': len(game.decks['2']),
                            },
                            'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                            'center_tile_control': game.center_tile_control
                        }))

            elif data['type'] == 'resolve-land':
                    slot = data['slot']
                    target = data['target']
                    card = game.hands[user_id][slot]

                    if hasattr(card, "resolve_with_input"):
                        # 👇 Try resolving first — don't remove card or spend mana yet
                        success, info = card.resolve_with_input(game, user_id, target)

                        if success:
                            game.hands[user_id].pop(slot)
                            game.graveyard[user_id].append(card)
                            game.mana[user_id] -= card.mana

                        serialized_board = [[p.to_dict() if p else None for p in row] for row in game.board]
                        serialized_land_board = [[p.to_dict() if p else None for p in row] for row in game.land_board]
                        for ws_conn in connected_users[game_id].values():
                            ws_conn.send(json.dumps({
                                'type': 'update',
                                'board': serialized_board,
                                'land_board': serialized_land_board,
                                'hand1': [c.to_dict() for c in game.hands['1']],
                                'hand2': [c.to_dict() for c in game.hands['2']],
                                'turn': game.current_player,
                                'success': success,
                                'mana': game.mana,
                                'graveyard': {
                                    '1': [c.to_dict() for c in game.graveyard['1']],
                                    '2': [c.to_dict() for c in game.graveyard['2']],
                                },
                                'deck_sizes': {
                                    '1': len(game.decks['1']),
                                    '2': len(game.decks['2']),
                                },
                                'info': info,
                                'moves_left': game.max_moves_per_turn - game.moves_this_turn,
                                'center_tile_control': game.center_tile_control

                            }))

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if user_id and user_id in connected_users[game_id]:
            del connected_users[game_id][user_id]


if __name__ == '__main__':
    app.run(debug=True)
