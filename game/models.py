from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from PIL import Image
import datetime
import uuid
from django.utils import timezone

# Create your models here.

class Deck(models.Model):
    """Model representing a deck of cards (either reference or game-specific)"""
    DECK_TYPES = [
        ('reference', 'Reference Deck'),
        ('game', 'Game Deck'),
    ]
    
    deck_type = models.CharField(max_length=20, choices=DECK_TYPES, default='reference')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    game = models.ForeignKey('Game', on_delete=models.CASCADE, null=True, blank=True, related_name='decks')
    
    def __str__(self):
        if self.game:
            return f"{self.name} - {self.game.title}"
        return f"{self.name} (Reference)"
    
    def create_game_copy(self, game):
        """Create a copy of this deck for a specific game"""
        if self.deck_type != 'reference':
            raise ValueError("Can only create game copies from reference decks")
        
        game_deck = Deck.objects.create(
            deck_type='game',
            name=self.name,
            game=game
        )
        
        # Copy all cards from reference deck to game deck
        for card in self.cards.all():
            card.create_game_copy(game_deck)
        
        return game_deck


class Card(models.Model):
    """Model representing a card in the game"""
    CARD_TYPES = [
        ('character', 'Character'),
        ('motive', 'Motive'),
        ('location', 'Location'),
        ('clue', 'Clue'),
        ('suspect', 'Suspect'),
    ]
    
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    front_image = models.ImageField(upload_to='cards/fronts/', null=True, blank=True)
    back_image = models.ImageField(upload_to='cards/backs/', null=True, blank=True)
    card_type = models.CharField(max_length=20, choices=CARD_TYPES)
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='cards')
    created_at = models.DateTimeField(auto_now_add=True)
    revealed = models.BooleanField(default=False)
    reveal_time = models.IntegerField(null=True, blank=True, help_text="Time in minutes when this card is revealed")
    
    def __str__(self):
        return f"{self.get_card_type_display()}: {self.title}"
    
    def create_game_copy(self, game_deck):
        """Create a copy of this card for a specific game deck"""
        return Card.objects.create(
            title=self.title,
            description=self.description,
            front_image=self.front_image,
            back_image=self.back_image,
            card_type=self.card_type,
            deck=game_deck,
            reveal_time=self.reveal_time,
            revealed=False
        )
    
    def reveal(self):
        """Reveal this card"""
        self.revealed = True
        self.save()
    
    def should_reveal(self, game_time_elapsed):
        """Check if this card should be revealed based on game time"""
        if self.reveal_time and not self.revealed:
            return game_time_elapsed >= self.reveal_time
        return False


class Game(models.Model):
    """Model representing a game session"""
    STATUS_CHOICES = [
        ('setup', 'Setup'),
        ('in_progress', 'In Progress'),
        ('finished', 'Finished'),
    ]
    
    title = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='setup')
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    join_code = models.CharField(max_length=8, unique=True, blank=True)
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Generate a unique join code if not provided
        if not self.join_code:
            self.join_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)
    
    def start_game(self):
        """Start the game and set the timer"""
        if self.status == 'setup':
            from django.db.models import Count
            import random
            
            # Start transaction to ensure all card dealing is atomic
            from django.db import transaction
            with transaction.atomic():
                # Set game status and timer
                self.status = 'in_progress'
                self.start_time = timezone.now()
                self.end_time = self.start_time + datetime.timedelta(minutes=90)
                self.save()
                
                # Create system message for game start
                Message.objects.create(
                    game=self,
                    content="The game has started. You have 90 minutes to find Alice.",
                    is_system_message=True
                )
                
                # Get reference deck
                try:
                    reference_deck = Deck.objects.get(deck_type='reference', game__isnull=True)
                except Deck.DoesNotExist:
                    Message.objects.create(
                        game=self,
                        content="ERROR: Reference deck not found! Cards could not be dealt.",
                        is_system_message=True
                    )
                    return True
                
                # Create game deck for this game
                game_deck = Deck.objects.create(
                    name=f"Game Deck for {self.title}",
                    deck_type='game',
                    game=self
                )
                
                # Get players for this game
                players = self.players.all()
                player_count = players.count()
                
                if player_count < 3:
                    Message.objects.create(
                        game=self,
                        content="Warning: This game works best with 3-5 players.",
                        is_system_message=True
                    )
                
                # Get all card types from reference deck
                character_cards = list(reference_deck.cards.filter(card_type='character'))
                location_cards = list(reference_deck.cards.filter(card_type='location'))
                motive_cards = list(reference_deck.cards.filter(card_type='motive'))
                clue_cards = list(reference_deck.cards.filter(card_type='clue'))
                suspect_cards = list(reference_deck.cards.filter(card_type='suspect'))
                
                # Shuffle all card types
                random.shuffle(character_cards)
                random.shuffle(location_cards)
                random.shuffle(motive_cards)
                random.shuffle(clue_cards)
                random.shuffle(suspect_cards)
                
                # Assign character cards based on player character selections
                character_map = {}
                for card in character_cards:
                    character_map[card.title] = card
                
                # Deal clue cards
                # We need to calculate how many clue cards per player
                total_clue_cards = min(len(clue_cards), player_count * 2)  # 1-2 clue cards per player
                clues_per_player = total_clue_cards // player_count
                
                # Create a copy of each card in the game deck
                # Track which game cards correspond to which reference cards
                game_card_map = {}
                
                # Copy all needed cards to game deck
                cards_to_copy = []
                cards_to_copy.extend(character_cards[:player_count])
                cards_to_copy.extend(location_cards[:player_count])
                cards_to_copy.extend(motive_cards[:1])  # Just one motive card for the game
                cards_to_copy.extend(clue_cards[:total_clue_cards])
                cards_to_copy.extend(suspect_cards[:player_count])
                
                # Copy cards to game deck
                for ref_card in cards_to_copy:
                    game_card = Card.objects.create(
                        title=ref_card.title,
                        description=ref_card.description,
                        front_image=ref_card.front_image,
                        back_image=ref_card.back_image,
                        card_type=ref_card.card_type,
                        deck=game_deck,
                        reveal_time=ref_card.reveal_time,
                        revealed=False
                    )
                    game_card_map[ref_card.id] = game_card
                
                # Deal cards to players
                for i, player in enumerate(players):
                    # Get player's hand
                    hand, created = Hand.objects.get_or_create(player=player, game=self)
                    
                    # Assign character card based on character name
                    character_assigned = False
                    for char_card in character_cards:
                        if player.character_name in char_card.title or char_card.title in player.character_name:
                            if char_card.id in game_card_map:
                                # Assign the character card to player
                                player.character_card = game_card_map[char_card.id]
                                player.save()
                                character_assigned = True
                                break
                    
                    # If no character card matched by name, assign one randomly
                    if not character_assigned and i < len(character_cards) and character_cards[i].id in game_card_map:
                        player.character_card = game_card_map[character_cards[i].id]
                        player.save()
                    
                    # Deal clue cards
                    clue_start_idx = i * clues_per_player
                    for j in range(clues_per_player):
                        if clue_start_idx + j < len(clue_cards) and clue_cards[clue_start_idx + j].id in game_card_map:
                            hand.cards.add(game_card_map[clue_cards[clue_start_idx + j].id])
                    
                    # Each player gets one location card
                    if i < len(location_cards) and location_cards[i].id in game_card_map:
                        hand.cards.add(game_card_map[location_cards[i].id])
                    
                    # Each player gets one suspect card
                    if i < len(suspect_cards) and suspect_cards[i].id in game_card_map:
                        hand.cards.add(game_card_map[suspect_cards[i].id])
                
                # Deal the motive card to a random player
                if motive_cards and motive_cards[0].id in game_card_map:
                    random_player = random.choice(players)
                    random_hand = Hand.objects.get(player=random_player, game=self)
                    random_hand.cards.add(game_card_map[motive_cards[0].id])
                
                # Create system message about cards
                Message.objects.create(
                    game=self,
                    content="Cards have been dealt. Check your hand to see your cards.",
                    is_system_message=True
                )
                
            return True
        return False
    
    def end_game(self):
        """End the game"""
        if self.status == 'in_progress':
            self.status = 'finished'
            self.save()
            
            # Create system message for game end
            Message.objects.create(
                game=self,
                content="The game has ended.",
                is_system_message=True
            )
            
            return True
        return False
    
    def time_remaining(self):
        """Get the remaining time in minutes"""
        if self.status != 'in_progress' or not self.end_time:
            return 0
        
        remaining = self.end_time - timezone.now()
        
        # If time is up, end the game
        if remaining.total_seconds() <= 0:
            self.end_game()
            return 0
        
        # Return minutes
        return int(remaining.total_seconds() / 60)
    
    def time_elapsed(self):
        """Get the elapsed time in minutes"""
        if self.status != 'in_progress' or not self.start_time:
            return 0
        
        elapsed = timezone.now() - self.start_time
        return int(elapsed.total_seconds() / 60)
    
    def check_card_reveals(self):
        """Check and reveal cards based on elapsed time"""
        if self.status != 'in_progress':
            return
        
        elapsed_minutes = self.time_elapsed()
        
        # Get all game decks for this game
        for deck in self.decks.filter(deck_type='game'):
            # Get all unrevealed cards with reveal times
            cards_to_check = deck.cards.filter(revealed=False).exclude(reveal_time=None)
            
            for card in cards_to_check:
                if card.should_reveal(elapsed_minutes):
                    card.reveal()
                    
                    # Create system message for card reveal
                    Message.objects.create(
                        game=self,
                        content=f"A new clue has been revealed: {card.title}",
                        is_system_message=True
                    )


class Player(models.Model):
    """Model representing a player in the game"""
    PLAYER_COLORS = [
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('purple', 'Purple'),
        ('pink', 'Pink'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='players')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='players')
    character_name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, choices=PLAYER_COLORS)
    is_host = models.BooleanField(default=False)
    character_card = models.ForeignKey(Card, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_to')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['game', 'color'], ['game', 'character_name']]
    
    def __str__(self):
        return f"{self.character_name} ({self.get_color_display()}) in {self.game.title}"
    
    def can_start_game(self):
        """Check if this player can start the game (must be host)"""
        return self.is_host and self.game.status == 'setup'
    
    def can_send_message(self):
        """Check if this player can send a message (game must be in progress)"""
        return self.game.status == 'in_progress'


class Hand(models.Model):
    """Model representing a player's hand of cards"""
    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name='hand')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='hands')
    cards = models.ManyToManyField(Card, related_name='in_hands')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Hand of {self.player.character_name}"
    
    def add_card(self, card):
        """Add a card to the hand"""
        self.cards.add(card)
    
    def remove_card(self, card):
        """Remove a card from the hand"""
        self.cards.remove(card)


def get_message_image_path(instance, filename):
    """Generate a unique file path for message images"""
    # Get the file extension
    ext = filename.split('.')[-1].lower()
    
    # Generate timestamp in format YYYYMMDD_HHMMSS
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    
    # Generate a UUID
    unique_id = str(uuid.uuid4())[:8]
    
    # Create new filename with timestamp and UUID
    new_filename = f"{timestamp}_{unique_id}.{ext}"
    
    # Store all message images in a single directory
    return f'messages/{new_filename}'


class Message(models.Model):
    SYSTEM_TYPES = [
        ('alert', 'Alert'),
        ('success', 'Success'),
        ('info', 'Info'),
        ('warning', 'Warning'),
    ]

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, related_name='sent_messages')
    recipient = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, related_name='received_messages')
    content = models.TextField()
    image = models.ImageField(upload_to=get_message_image_path, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_system_message = models.BooleanField(default=False)
    system_type = models.CharField(max_length=10, choices=SYSTEM_TYPES, null=True, blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        if self.is_system_message:
            return f"System Message: {self.content[:50]}"
        return f"{self.sender.character_name if self.sender else 'Unknown'} to {self.recipient.character_name if self.recipient else 'Everyone'}: {self.content[:50]}"
