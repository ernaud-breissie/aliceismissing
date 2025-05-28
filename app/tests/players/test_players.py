from django.test import TestCase
from django.contrib.auth.models import User
from game.models import Game, Player, Card, Deck, Hand

class PlayerTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testplayer',
            password='testpass123'
        )
        self.game = Game.objects.create(
            title='Test Game'
        )
        self.deck = Deck.objects.create(
            name='Test Deck',
            deck_type='game',
            game=self.game
        )

    def test_player_creation(self):
        """Test player creation"""
        player = Player.objects.create(
            user=self.user,
            game=self.game,
            character_name='Test Character',
            color='blue'
        )
        self.assertEqual(player.character_name, 'Test Character')
        self.assertEqual(player.color, 'blue')
        self.assertFalse(player.is_host)

    def test_player_as_host(self):
        """Test player as game host"""
        player = Player.objects.create(
            user=self.user,
            game=self.game,
            character_name='Test Character',
            color='blue',
            is_host=True
        )
        self.assertTrue(player.is_host)
        self.assertTrue(player.can_start_game())

    def test_player_character_card(self):
        """Test player character card assignment"""
        card = Card.objects.create(
            title='Character Card',
            card_type='character',
            deck=self.deck
        )
        player = Player.objects.create(
            user=self.user,
            game=self.game,
            character_name='Test Character',
            color='blue',
            character_card=card
        )
        self.assertEqual(player.character_card, card)

    def test_player_hand(self):
        """Test player hand creation and card management"""
        player = Player.objects.create(
            user=self.user,
            game=self.game,
            character_name='Test Character',
            color='blue'
        )
        hand = Hand.objects.create(
            player=player,
            game=self.game
        )
        card = Card.objects.create(
            title='Test Card',
            card_type='clue',
            deck=self.deck
        )
        hand.add_card(card)
        self.assertIn(card, hand.cards.all())

