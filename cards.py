from card_types import Monster, Sorcery

# prompt - great, now let's generate some images, they should be high quality, square
#
# style should be evocative of old school anime, but also old school western animation, though very realistic and very stylized, little line work, full body shots, and a lot of camera perspective, let's try bonecrawler first

class Bonecrawler(Monster):  # Formerly: Pawn
    name = "Bonecrawler"
    movement = {
        "forward": 1,
        'left': 1
    }
    original_attack = 100
    original_defense = 200

    def __init__(self, owner):
        super().__init__(
            card_id='bonecrawler',
            owner=owner,
            attack=self.original_attack,
            defense=self.original_defense,
            image='/static/cards/bonecrawler.png',
            mana=1
        )


class ShadowVine(Monster):  # Formerly: DiagonalRanger
    name = "Shadow Vine"
    movement = {
        "forward-left": 'any',
        "forward-right": 'any',
        "back-left": 'any',
        "back-right": 'any'
    }
    original_attack = 200
    original_defense = 200

    def __init__(self, owner):
        super().__init__(
            card_id='shadow_vine',
            owner=owner,
            attack=self.original_attack,
            defense=self.original_defense,
            image='/static/cards/shadow_vine.png',
            mana=3
        )


class DreadmawQueen(Monster):  # Formerly: Queen
    name = "Dreadmaw Queen"
    movement = {
        "forward": 'any',
        "forward-left": 'any',
        "forward-right": 'any',
        "right": 'any',
        "back-left": 'any',
        "left": 'any',
        "back-right": 'any',
        "back": 'any'
    }
    original_attack = 170
    original_defense = 130

    def __init__(self, owner):
        super().__init__(
            card_id='dreadmaw_queen',
            owner=owner,
            attack=self.original_attack,
            defense=self.original_defense,
            image='/static/cards/dreadmaw_queen.png',
            mana=4
        )

class FrostRevenant(Monster):
    name = "Frost Revenant"
    movement = {
        "forward": 'any',
        "back-left": 1,
        "back-right": 1
    }
    original_attack = 180
    original_defense = 150

    def __init__(self, owner):
        super().__init__(
            card_id='frost_revenant',
            owner=owner,
            attack=self.original_attack,
            defense=self.original_defense,
            image='/static/cards/frost_revenant.png',
            mana=3
        )


class SolarPaladin(Monster):
    name = "Solar Paladin"
    movement = {
        "forward": 'any',
        "back": 'any',
        "left": 'any',
        "right": 'any'
    }

    original_attack = 230
    original_defense = 130

    def __init__(self, owner):
        super().__init__(
            card_id='solar_paladin',
            owner=owner,
            attack=self.original_attack,
            defense=self.original_defense,
            image='/static/cards/solar_paladin.png',
            mana=4
        )

class SylvanArcher(Monster):
    name = "Sylvan Archer"
    movement = {
        "forward-left": 1,
        "forward-right": 1,
        "back-left": 1,
        "back-right": 1
    }

    original_attack = 130
    original_defense = 200

    def __init__(self, owner):
        super().__init__(
            card_id='sylvan_archer',
            owner=owner,
            attack=self.original_attack,
            defense=self.original_defense,
            image='/static/cards/sylvan_archer.png',
            mana=2
        )



class Magistra(Monster):
    name = "Magistra"
    movement = {
        "forward": 1,
        "left": 'any',
        "right": 'any',
        "back-left": 1,
        "back-right": 1
    }

    original_attack = 170
    original_defense = 190

    def __init__(self, owner):
        super().__init__(
            card_id='magistra',
            owner=owner,
            attack=self.original_attack,
            defense=self.original_defense,
            image='/static/cards/magistra.png',
            mana=3
        )



class LordOfTheAbyss(Monster):
    name = "Lord of the Abyss"
    movement = {
        "forward": 'any',
        "left": 1,
        "right": 1,
        "back-left": 'any',
        "back-right": 'any',
        'back': 1
    }
    original_attack = 220
    original_defense = 200

    def __init__(self, owner):
        super().__init__(
            card_id='lord_of_the_abyss',
            owner=owner,
            attack=self.original_attack,
            defense=self.original_defense,
            image='/static/cards/lord_of_the_abyss.png',
            mana=4
        )


class Stormcaller(Monster):
    name = "Stormcaller"
    movement = {
        "forward-right": 'any',
        "left": 1,
        "right": 1,
        "back-left": 1,
        "back-right": 1
    }
    original_attack = 170
    original_defense = 190

    def __init__(self, owner):
        super().__init__(
            card_id='stormcaller',
            owner=owner,
            attack=self.original_attack,
            defense=self.original_defense,
            image='/static/cards/stormcaller.png',
            mana=3
        )



class WingsOfTheShatteredSkies(Monster):
    name = "Wings of the Shattered Skies"
    movement = {
        'forward': 'any',
        "forward-right": 1,
        "forward-left": 1,
        "back-left": 1,
        "back-right": 1
    }

    original_attack = 150
    original_defense = 170

    def __init__(self, owner):
        super().__init__(
            card_id='wings_of_the_shattered_skies',
            owner=owner,
            attack=self.original_attack,
            defense=self.original_defense,
            image='/static/cards/wings_of_the_shattered_skies.png',
            mana=2
        )

class BlazingRain(Sorcery):
    name = 'Blazing Rain'
    text = "Weaken all opponent's DEF by 50."
    activation_needs = ["back", "forward"]
    def __init__(self, owner):
        super().__init__('blazing_rain', owner, image='/static/cards/blazing_rain.png', mana=2)


    def affect_board(self, game, target_pos, user_id):
        for row in game.board:
            for i, card in enumerate(row):
                if card and card.owner != user_id and isinstance(card, Monster):
                    card.defense -= 50
                    if card.defense <= 0:
                        game.graveyard[card.owner].append(card)
                        row[i] = None


class NaturesResurgence(Sorcery):
    name = 'Natures Resurgence'
    text = 'Increase the DEF of your monsters by 30.'
    activation_needs = ["forward", "forward-right"]
    def __init__(self, owner):
        super().__init__('natures_resurgence', owner, image='/static/cards/natures_resurgence.png', mana=1)

    def affect_board(self, game, target_pos, user_id):
        for row in game.board:
            for card in row:
                if card and card.owner == user_id and isinstance(card, Monster):
                    card.defense += 30


class MysticDraw(Sorcery):
    name = 'Mystic Draw'
    text = 'Draw 2 cards.'
    activation_needs = ["left", "forward"]
    def __init__(self, owner):
        super().__init__('mystic_draw', owner, image='/static/cards/mystic_draw.png', mana=2)

    def affect_board(self, game, target_pos, user_id):
        for _ in range(2):
            if game.decks[user_id]:
                game.hands[user_id].append(game.decks[user_id].pop(0))


class DivineReset(Sorcery):
    name = 'Divine Reset'
    text = 'Destroy all monsters on the field.'
    activation_needs = ["left", "right"]
    def __init__(self, owner):
        super().__init__(
            card_id='divine_reset',
            owner=owner,
            image='/static/cards/divine_reset.png',
            mana=2
        )

    def affect_board(self, game, target_pos, user_id):
        for row in game.board:
            for i, card in enumerate(row):
                if card and isinstance(card, Monster):
                    game.graveyard[card.owner].append(card)
                    row[i] = None

