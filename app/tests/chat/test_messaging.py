from django.test import TestCase
from django.contrib.auth.models import User
from game.models import Game, Player, Message

class ChatMessagingTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.game = Game.objects.create(
            title='Test Game'
        )
        self.player = Player.objects.create(
            user=self.user,
            game=self.game,
            character_name='Test Character',
            color='blue'
        )

    def test_basic_messaging(self):
        """Test basic message creation"""
        message = Message.objects.create(
            game=self.game,
            sender=self.player,
            content='Test message'
        )
        self.assertEqual(message.content, 'Test message')
        self.assertEqual(message.sender, self.player)
        self.assertFalse(message.is_system_message)

    def test_system_message(self):
        """Test system message creation"""
        system_message = Message.objects.create(
            game=self.game,
            content='System message',
            is_system_message=True,
            system_type='info'
        )
        self.assertTrue(system_message.is_system_message)
        self.assertEqual(system_message.system_type, 'info')
        self.assertIsNone(system_message.sender)

