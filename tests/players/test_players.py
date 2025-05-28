from django.test import TestCase
from django.contrib.auth.models import User

class PlayerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testplayer',
            password='testpass123'
        )

    def test_player_creation(self):
        self.assertEqual(self.user.username, 'testplayer')

