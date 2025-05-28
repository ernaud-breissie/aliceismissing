from django.test import TestCase
from django.contrib.auth.models import User
from game.models import Game, Player, Message
from django.core.files.uploadedfile import SimpleUploadedFile

class MessageTests(TestCase):
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
        self.recipient = Player.objects.create(
            user=User.objects.create_user('recipient', 'recipient@test.com', 'pass123'),
            game=self.game,
            character_name='Recipient Character',
            color='green'
        )

    def test_message_creation(self):
        """Test message creation with recipient"""
        message = Message.objects.create(
            game=self.game,
            sender=self.player,
            recipient=self.recipient,
            content='Test private message'
        )
        self.assertEqual(message.content, 'Test private message')
        self.assertEqual(message.sender, self.player)
        self.assertEqual(message.recipient, self.recipient)
        self.assertFalse(message.is_system_message)

    def test_system_alert_message(self):
        """Test system alert message"""
        alert = Message.objects.create(
            game=self.game,
            content='Alert message',
            is_system_message=True,
            system_type='alert'
        )
        self.assertTrue(alert.is_system_message)
        self.assertEqual(alert.system_type, 'alert')

