import uuid


class Card:
    name = "Default Card"
    def __init__(self, card_type, card_id, owner, image='', mana=0):
        self.id = str(uuid.uuid4())      # unique instance ID
        self.card_id = card_id           # shared ID for this card type
        self.type = card_type            # 'monster', 'land', or 'sorcery'
        self.owner = owner               # user who owns it
        self.image = image
        self.mana = mana

    def to_dict(self):
        return {
            'name': self.name,
            'id': self.id,
            'card_id': self.card_id,
            'type': self.type,
            'owner': self.owner,
            'image': self.image,
            'mana': self.mana
        }

class Monster(Card):
    movement = {}
    original_attack = 0
    original_defense = 0

    def __init__(self, card_id, owner, attack, defense, image='', mana=0):
        super().__init__('monster', card_id, owner, image, mana)
        self.attack = attack
        self.defense = defense

    def to_dict(self):
        base = super().to_dict()
        base.update({
            'attack': self.attack,
            'defense': self.defense,
            'movement': self.movement,
            'original_attack': self.original_attack,
            'original_defense': self.original_defense,

        })
        return base


    @staticmethod
    def can_move(card, from_pos, to_pos, board):
        fx, fy = from_pos
        tx, ty = to_pos
        dx, dy = tx - fx, ty - fy

        if dx == 0 and dy == 0:
            return False  # no movement

        # Normalize deltas to direction unit vectors
        dir_x = 0 if dx == 0 else dx // abs(dx)
        dir_y = 0 if dy == 0 else dy // abs(dy)

        direction = Monster.resolve_direction(dir_x, dir_y, card.owner)
        if not direction:
            return False

        allowed_range = card.__class__.movement.get(direction)
        if not allowed_range:
            return False

        steps = max(abs(dx), abs(dy))
        if allowed_range != 'any' and steps > allowed_range:
            return False

        # Optional: check for blocking pieces between start and end
        # or add collision detection here if needed

        return True
    @staticmethod
    def resolve_direction(dx, dy, owner):
        # Flip perspective for owner '2'
        if owner == '2':
            dx = -dx
            dy = -dy

        direction_map = {
            (-1,  0): "forward",
            (-1, -1): "forward-left",
            (-1,  1): "forward-right",
            ( 0, -1): "left",
            ( 0,  1): "right",
            ( 1,  0): "back",
            ( 1, -1): "back-left",
            ( 1,  1): "back-right"
        }
        return direction_map.get((dx, dy))

#
# # Land and Sorcery could also subclass Card
# class Land(Card):
#     def __init__(self, card_id, owner, mana_type, image='', mana=0):
#         super().__init__('land', card_id, owner, image, mana)
#         self.mana_type = mana_type
#
#     def to_dict(self):
#         base = super().to_dict()
#         base['mana_type'] = self.mana_type
#         return base
#
#

class Sorcery(Card):
    activation_needs = [] # default: no constraints
    text = ''
    def __init__(self, card_id, owner, image='', mana=0):
        super().__init__('sorcery', card_id, owner, image, mana)


    def can_activate(self, board, x, y):
        for direction in self.activation_needs:
            if not satisfies_activation_need(board, x, y, direction, self.owner):
                return False
        return True

    def affect_board(self, game, user_id):
        """
        Override this in subclasses to define what the card does.
        """
        pass

    def to_dict(self):
        base = super().to_dict()
        base['activation_needs'] = self.activation_needs
        base['text'] = self.text
        base['effect'] = self.__class__.__name__  # optional, for display
        return base


def satisfies_activation_need(board, x, y, direction, owner):
    dx, dy = get_direction_offset(direction)
    tx, ty = x + dx, y + dy
    if not (0 <= tx < len(board) and 0 <= ty < len(board[0])):
        return False

    opposite = {
        "forward": "back",
        "back": "forward",
        "left": "right",
        "right": "left",
        "forward-left": "back-right",
        "forward-right": "back-left",
        "back-left": "forward-right",
        "back-right": "forward-left"
    }

    opposite_dir = opposite[direction]

    # 👉 Check tile in "direction"
    card = board[tx][ty]
    if isinstance(card, Monster):
        dx1, dy1 = get_direction_offset(opposite_dir)  # ❗️No owner here
        monster_dir = Monster.resolve_direction(dx1, dy1, card.owner)
        movement_val = card.movement.get(monster_dir)
        if movement_val == 1 or movement_val == 'any':
            return True

    # 👉 Check tile in "opposite direction"
    ox, oy = x - dx, y - dy
    if 0 <= ox < len(board) and 0 <= oy < len(board[0]):
        card = board[ox][oy]
        if isinstance(card, Monster):
            dx2, dy2 = get_direction_offset(direction)  # again no owner
            monster_dir = Monster.resolve_direction(dx2, dy2, card.owner)
            movement_val = card.movement.get(monster_dir)
            if movement_val == 1 or movement_val == 'any':
                return True
    print('failing on line 179')
    return False




def get_direction_offset(direction, owner=None):
    # Always treat forward as up (player 1's perspective)
    forward = -1
    mapping = {
        "forward": (forward, 0),
        "back": (-forward, 0),
        "left": (0, -1),
        "right": (0, 1),
        "forward-left": (forward, -1),
        "forward-right": (forward, 1),
        "back-left": (-forward, -1),
        "back-right": (-forward, 1),
    }
    return mapping.get(direction)

