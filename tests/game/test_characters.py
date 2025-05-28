from django.test import TestCase
from game.models import Card, Deck, Game

class CardTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.game = Game.objects.create(
            title='Test Game'
        )
        self.deck = Deck.objects.create(
            name='Test Deck',
            deck_type='reference',
            game=self.game
        )

    def test_character_card_creation(self):
        """Test character card creation"""
        card = Card.objects.create(
            title='Test Character',
            description='A test character',
            card_type='character',
            deck=self.deck
        )
        self.assertEqual(card.title, 'Test Character')
        self.assertEqual(card.card_type, 'character')
        self.assertFalse(card.revealed)

    def test_card_reveal(self):
        """Test card reveal functionality"""
        card = Card.objects.create(
            title='Test Character',
            description='A test character',
            card_type='character',
            deck=self.deck,
            reveal_time=30
        )
        self.assertFalse(card.revealed)
        self.assertTrue(card.should_reveal(35))
        card.reveal()
        self.assertTrue(card.revealed)
