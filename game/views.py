import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.urls import reverse
import json

from .models import Game, Player, Card, Deck, Hand, Message

# Configure logger
logger = logging.getLogger('game')

# Authentication Views
def register(request):
    """Register a new user"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('home')
    else:
        form = UserCreationForm()
    
    return render(request, 'game/register.html', {'form': form})

# Game Views
@login_required
def home(request):
    """Display user's games and available games"""
    # Get games the user is part of
    user_games = Player.objects.filter(user=request.user).select_related('game')
    
    # Get games in setup state that the user is not part of
    available_games = Game.objects.filter(status='setup').exclude(
        players__user=request.user
    )
    
    context = {
        'user_games': user_games,
        'available_games': available_games,
    }
    
    return render(request, 'game/home.html', context)

@login_required
def new_game(request):
    """Create a new game"""
    if request.method == 'POST':
        title = request.POST.get('title', f"Alice Search - {timezone.now().strftime('%b %d, %Y')}")
        
        with transaction.atomic():
            # Create a new game
            game = Game.objects.create(
                title=title,
                status='setup'
            )
            
            # Make the current user the host
            player = Player.objects.create(
                user=request.user,
                game=game,
                character_name='',  # Will be set during character selection
                color='',  # Will be set during character selection
                is_host=True
            )
            
            # Create a welcome system message
            create_system_message(
                game,
                "Game created. Invite players using the join code: " + game.join_code,
                "info"
            )
            
            # Create the initial hand for this player
            Hand.objects.create(
                player=player,
                game=game
            )
            
            # Create a game deck from the reference deck (will be implemented later)
            
        messages.success(request, f'Game "{title}" created successfully!')
        return redirect('game_setup', game_id=game.id)
    
    return render(request, 'game/new_game.html')

@login_required
def join_game(request):
    """Join a game using a join code"""
    if request.method == 'POST':
        join_code = request.POST.get('join_code', '').strip().upper()
        
        try:
            game = Game.objects.get(join_code=join_code, status='setup')
            
            # Check if user is already in this game
            if Player.objects.filter(user=request.user, game=game).exists():
                messages.info(request, f'You are already part of the game "{game.title}"')
                return redirect('game_detail', game_id=game.id)
            
            # Create player and hand
            with transaction.atomic():
                player = Player.objects.create(
                    user=request.user,
                    game=game,
                    character_name='',  # Will be set during character selection
                    color='',  # Will be set during character selection
                )
                
                # Create player's hand
                Hand.objects.create(
                    player=player,
                    game=game
                )
                
                # Create a system message about the player joining
                create_system_message(
                    game,
                    f"{request.user.username} has joined the game.",
                    "info"
                )
            
            messages.success(request, f'You have joined the game "{game.title}"')
            return redirect('game_setup', game_id=game.id)
            
        except Game.DoesNotExist:
            messages.error(request, 'Invalid game code or the game has already started')
            return redirect('home')
    
    return redirect('home')

@login_required
def join_game_with_code(request, join_code):
    """Direct link to join a game with a specific code"""
    # This reuses the logic from join_game, but with the code from the URL
    request.method = 'POST'
    request.POST = request.POST.copy()
    request.POST['join_code'] = join_code
    return join_game(request)

@login_required
def game_detail(request, game_id):
    """View game messages"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure user is part of this game
    try:
        player = Player.objects.get(user=request.user, game=game)
    except Player.DoesNotExist:
        messages.error(request, "You are not part of this game")
        return redirect('home')
    
    # If game is in progress, update card reveals
    if game.status == 'in_progress':
        game.check_card_reveals()
    
    context = {
        'game': game,
        'player': player,
    }
    
    # Determine template based on game status
    if game.status == 'setup':
        return redirect('game_setup', game_id=game.id)
    else:
        # Get the player's hand
        hand = Hand.objects.get(player=player, game=game)
        context['hand'] = hand
        
        # Get messages in chronological order (oldest to newest)
        db_messages = Message.objects.filter(game=game).order_by('timestamp')
        
        # Format messages for the template
        initial_messages_data = []
        for msg in db_messages:
            message_data = {
                'id': msg.id,
                'type': 'system' if msg.is_system_message else 'sent' if msg.sender == player else 'received',
                'isDirect': bool(msg.recipient),
                'content': msg.content,
                'time': msg.timestamp.strftime('%H:%M')
            }
            
            if not msg.is_system_message and msg.sender:
                message_data['sender'] = {
                    'name': msg.sender.character_name,
                    'color': msg.sender.color
                }
            
            if msg.recipient:
                message_data['recipient'] = msg.recipient.character_name
            
            if msg.image:
                message_data['image'] = {
                    'url': msg.image.url,
                    'detailUrl': reverse('message_detail', args=[game.id, msg.id])
                }
            
            initial_messages_data.append(message_data)
        
        # Pass the messages data to the template
        context['initial_messages_json'] = initial_messages_data
        
        # Get recently revealed cards
        context['revealed_cards'] = Card.objects.filter(
            deck__game=game, 
            revealed=True
        ).order_by('-reveal_time')[:6]
        
        return render(request, 'game/game_detail.html', context)

@login_required
def game_info(request, game_id):
    """View game information and details"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure user is part of this game
    try:
        player = Player.objects.get(user=request.user, game=game)
    except Player.DoesNotExist:
        messages.error(request, "You are not part of this game")
        return redirect('home')
    
    context = {
        'game': game,
        'player': player,
    }
    
    return render(request, 'game/game_info.html', context)

@login_required
def game_setup(request, game_id):
    """Setup page for a game before it starts"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure the game is in setup status
    if game.status != 'setup':
        return redirect('game_detail', game_id=game.id)
    
    # Ensure user is part of this game
    try:
        player = Player.objects.get(user=request.user, game=game)
    except Player.DoesNotExist:
        messages.error(request, "You are not part of this game")
        return redirect('home')
    
    # Get all players in this game
    players = Player.objects.filter(game=game)
    
    context = {
        'game': game,
        'player': player,
        'players': players,
        'is_host': player.is_host,
    }
    
    return render(request, 'game/game_setup.html', context)

@login_required
def start_game(request, game_id):
    """Start a game in setup mode"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure the game is in setup status
    if game.status != 'setup':
        messages.error(request, "This game has already started")
        return redirect('game_detail', game_id=game.id)
    
    # Ensure user is host of this game
    try:
        player = Player.objects.get(user=request.user, game=game, is_host=True)
    except Player.DoesNotExist:
        messages.error(request, "Only the host can start the game")
        return redirect('game_setup', game_id=game.id)
    
    # Ensure all players have selected characters
    incomplete_players = Player.objects.filter(
        game=game, 
        character_name=''
    ).exists()
    
    if incomplete_players:
        messages.error(request, "All players must select a character before starting")
        return redirect('game_setup', game_id=game.id)
    
    # Start the game
    game.start_game()
    messages.success(request, "The game has started! You have 90 minutes to find Alice.")
    
    return redirect('game_detail', game_id=game.id)

@login_required
def end_game(request, game_id):
    """End a game in progress"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure the game is in progress
    if game.status != 'in_progress':
        messages.error(request, "This game is not in progress")
        return redirect('game_detail', game_id=game.id)
    
    # Ensure user is host of this game
    try:
        player = Player.objects.get(user=request.user, game=game, is_host=True)
    except Player.DoesNotExist:
        messages.error(request, "Only the host can end the game")
        return redirect('game_detail', game_id=game.id)
    
    # End the game
    game.end_game()
    messages.success(request, "The game has ended.")
    
    return redirect('game_detail', game_id=game.id)

@login_required
def select_character(request, game_id):
    """Select a character for the game"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure the game is in setup status
    if game.status != 'setup':
        messages.error(request, "Character selection is only available during setup")
        return redirect('game_detail', game_id=game.id)
    
    # Ensure user is part of this game
    try:
        player = Player.objects.get(user=request.user, game=game)
    except Player.DoesNotExist:
        messages.error(request, "You are not part of this game")
        return redirect('home')
    
    if request.method == 'POST':
        character_name = request.POST.get('character_name', '')
        color = request.POST.get('color', '')
        
        # Basic validation
        if not character_name or not color:
            messages.error(request, "Both character name and color are required")
            return redirect('select_character', game_id=game.id)
        
        # Check if the color is already taken in this game
        if Player.objects.filter(game=game, color=color).exclude(id=player.id).exists():
            messages.error(request, f"The color {color} has already been chosen by another player")
            return redirect('select_character', game_id=game.id)
        
        # Update player
        player.character_name = character_name
        player.color = color
        player.save()
        
        # Add system message
        create_system_message(
            game,
            f"{player.user.username} will be playing as {character_name}",
            "info"
        )
        
        messages.success(request, f"You are now playing as {character_name}")
        return redirect('game_setup', game_id=game.id)
    
    # Get available colors (not already chosen by other players)
    taken_colors = Player.objects.filter(game=game).exclude(id=player.id).values_list('color', flat=True)
    available_colors = [c for c, _ in Player.PLAYER_COLORS if c not in taken_colors]
    
    context = {
        'game': game,
        'player': player,
        'available_colors': available_colors,
    }
    
    return render(request, 'game/select_character.html', context)

@login_required
def assign_color(request, game_id):
    """Change player color (useful if we need this separate from character selection)"""
    # This is similar to select_character but only updates the color
    # Implementation is similar, so we'll skip the detailed code for now
    pass

@login_required
def game_timer(request, game_id):
    """API endpoint for the game timer"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure user is part of this game
    try:
        player = Player.objects.get(user=request.user, game=game)
    except Player.DoesNotExist:
        return HttpResponseForbidden("You are not part of this game")
    
    return JsonResponse({
        'time_remaining': game.time_remaining(),
        'status': game.status,
    })

@login_required
def game_status(request, game_id):
    """API endpoint for game status updates"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure user is part of this game
    try:
        player = Player.objects.get(user=request.user, game=game)
    except Player.DoesNotExist:
        return HttpResponseForbidden("You are not part of this game")
    
    # If game is in progress, update card reveals
    if game.status == 'in_progress':
        game.check_card_reveals()
    
    return JsonResponse({
        'status': game.status,
        'time_remaining': game.time_remaining(),
        'player_count': game.players.count(),
    })

@login_required
def player_hand(request, game_id):
    """View the player's hand of cards"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure user is part of this game
    try:
        player = Player.objects.get(user=request.user, game=game)
    except Player.DoesNotExist:
        messages.error(request, "You are not part of this game")
        return redirect('home')
    
    # Get the player's hand
    hand = get_object_or_404(Hand, player=player, game=game)
    
    context = {
        'game': game,
        'player': player,
        'hand': hand,
        'cards': hand.cards.all(),
    }
    
    return render(request, 'game/player_hand.html', context)

@login_required
def card_detail(request, game_id, card_id):
    """View details of a specific card"""
    game = get_object_or_404(Game, id=game_id)
    card = get_object_or_404(Card, id=card_id)
    
    # Ensure user is part of this game
    try:
        player = Player.objects.get(user=request.user, game=game)
    except Player.DoesNotExist:
        messages.error(request, "You are not part of this game")
        return redirect('home')
    
    # Ensure this card belongs to the player or is revealed
    hand = get_object_or_404(Hand, player=player, game=game)
    if not (card.revealed or card in hand.cards.all() or card == player.character_card):
        messages.error(request, "You don't have access to this card")
        return redirect('player_hand', game_id=game.id)
    
    context = {
        'game': game,
        'player': player,
        'card': card,
        'hand': hand,
    }
    
    return render(request, 'game/card_detail.html', context)


@login_required
def reveal_card(request, game_id, card_id):
    """Reveal a card to all players"""
    game = get_object_or_404(Game, id=game_id)
    card = get_object_or_404(Card, id=card_id)
    
    # Ensure user is part of this game
    try:
        player = Player.objects.get(user=request.user, game=game)
    except Player.DoesNotExist:
        messages.error(request, "You are not part of this game")
        return redirect('home')
    
    # Ensure the game is in progress
    if game.status != 'in_progress':
        messages.error(request, "Cards can only be revealed during an active game")
        return redirect('game_detail', game_id=game.id)
    
    # Ensure this card belongs to the player or is ready to be revealed
    hand = get_object_or_404(Hand, player=player, game=game)
    if not (card in hand.cards.all() or card == player.character_card):
        messages.error(request, "You don't have permission to reveal this card")
        return redirect('player_hand', game_id=game.id)
    
    # Check if the card should be revealed
    if not card.revealed:
        if card.should_reveal(game.time_elapsed()):
            card.reveal()
            
            # Create system message for card reveal
            create_system_message(
                game,
                f"{player.character_name} revealed a card: {card.title}",
                "success"
            )
            
            messages.success(request, f"You revealed the card: {card.title}")
        else:
            messages.error(request, "This card isn't ready to be revealed yet")
    else:
        messages.info(request, "This card has already been revealed")
    
    return redirect('card_detail', game_id=game.id, card_id=card.id)




@login_required
def send_message(request, game_id):
    """Send a message in the game"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure user is part of this game
    try:
        player = Player.objects.get(user=request.user, game=game)
    except Player.DoesNotExist:
        logger.warning(f"User {request.user.id} tried to send message in game {game_id} but is not a player.")
        return JsonResponse({'error': 'You are not part of this game'}, status=403)
    
    # Ensure the game is in progress
    if game.status != 'in_progress':
        logger.info(f"User {player.id} tried to send message in game {game_id} but game not in progress (status: {game.status}).")
        return JsonResponse({'error': 'Messages can only be sent during an active game'}, status=400)
    
    if request.method == 'POST':
        try:
            message_content = request.POST.get('message', '').strip()
            message_type = request.POST.get('message_type', 'public')
            recipient_id_str = request.POST.get('recipient')
            image = request.FILES.get('image')
            
            if not message_content and not image:
                logger.warning(f"Player {player.id} in game {game_id} tried to send an empty message.")
                return JsonResponse({'error': 'Message must contain text or an image'}, status=400)
            
            recipient = None
            if message_type == 'direct' and recipient_id_str:
                try:
                    recipient_id = int(recipient_id_str)
                    recipient = Player.objects.get(id=recipient_id, game=game)
                    if recipient == player:
                        logger.warning(f"Player {player.id} tried to send direct message to self in game {game_id}.")
                        return JsonResponse({'error': 'Cannot send a direct message to yourself.'}, status=400)
                except ValueError:
                    logger.error(f"Invalid recipient ID '{recipient_id_str}' for direct message by player {player.id} in game {game_id}.")
                    return JsonResponse({'error': 'Invalid recipient ID format.'}, status=400)
                except Player.DoesNotExist:
                    logger.warning(f"Recipient ID {recipient_id_str} not found for direct message by player {player.id} in game {game_id}.")
                    return JsonResponse({'error': 'Selected recipient not found'}, status=400)
            elif message_type == 'direct' and not recipient_id_str:
                logger.warning(f"Player {player.id} tried to send direct message without recipient in game {game_id}.")
                return JsonResponse({'error': 'Recipient required for direct message.'}, status=400)
            
            message = Message.objects.create(
                game=game,
                sender=player,
                recipient=recipient,
                content=message_content,
                image=image,
                is_system_message=False
            )
            logger.info(f"Message {message.id} created by player {player.id} in game {game_id}.")
            
            if recipient:
                create_system_message(
                    game,
                    f"{player.character_name} sent a direct message to {recipient.character_name}",
                    "info"
                )
            
            response_data = {
                'success': True,
                'message': {
                    'id': message.id,
                    'type': 'sent',
                    'isDirect': bool(recipient),
                    'content': message.content,
                    'sender': {
                        'name': player.character_name,
                        'color': player.color
                    },
                    'recipient': recipient.character_name if recipient else None,
                    'time': message.timestamp.strftime('%H:%M')
                }
            }
            
            if message.image:
                response_data['message']['image'] = {
                    'url': message.image.url,
                    'detailUrl': reverse('message_detail', args=[game.id, message.id])
                }
            
            return JsonResponse(response_data)
            
        except ValidationError as e:
            logger.error(f"ValidationError sending message for player {player.id} in game {game_id}: {e.message_dict}")
            return JsonResponse({'error': e.message_dict}, status=400)
        except Exception as e:
            logger.exception(f"Unexpected error sending message for player {player.id} in game {game_id}: {str(e)}")
            return JsonResponse({'error': 'An unexpected error occurred while sending your message.'}, status=500)
    
    logger.warning(f"Method not allowed for send_message in game {game_id} by user {request.user.id}.")
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def message_detail(request, game_id, message_id):
    """View a message's full-size image"""
    game = get_object_or_404(Game, id=game_id)
    message = get_object_or_404(Message, id=message_id, game=game)
    
    # Ensure user is part of this game
    try:
        player = Player.objects.get(user=request.user, game=game)
    except Player.DoesNotExist:
        messages.error(request, "You are not part of this game")
        return redirect('home')
    
    # Check if user has access to this message
    if message.recipient and message.recipient != player and message.sender != player:
        messages.error(request, "You don't have permission to view this message")
        return redirect('game_detail', game_id=game.id)
    
    context = {
        'game': game,
        'player': player,
        'message': message,
    }
    
    return render(request, 'game/message_detail.html', context)


# In-game Admin Views
@login_required
def game_admin(request, game_id):
    """Admin panel for game management"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure user is host of this game
    try:
        player = Player.objects.get(user=request.user, game=game, is_host=True)
    except Player.DoesNotExist:
        messages.error(request, "Only the host can access the admin panel")
        return redirect('game_detail', game_id=game.id)
    
    # Get game cards
    game_cards = Card.objects.filter(deck__game=game)
    
    # Get card types for the accordions
    card_types = [
        ('character', 'Character'),
        ('clue', 'Clue'),
        ('location', 'Location'),
        ('suspect', 'Suspect'),
        ('motive', 'Motive')
    ]
    
    # Get recent messages
    recent_messages = Message.objects.filter(game=game).order_by('-timestamp')[:20]
    
    context = {
        'game': game,
        'player': player,
        'game_cards': game_cards,
        'card_types': card_types,
        'recent_messages': recent_messages,
        'cards': game_cards,  # For the accordion sections
    }
    
    return render(request, 'game/game_admin.html', context)

@login_required
def game_admin_reset(request, game_id):
    """Reset a finished game to setup status"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure user is host of this game
    try:
        player = Player.objects.get(user=request.user, game=game, is_host=True)
    except Player.DoesNotExist:
        messages.error(request, "Only the host can reset the game")
        return redirect('game_admin', game_id=game.id)
    
    # Ensure game is in finished status
    if game.status != 'finished':
        messages.error(request, "Only finished games can be reset")
        return redirect('game_admin', game_id=game.id)
    
    # Reset game
    with transaction.atomic():
        game.status = 'setup'
        game.start_time = None
        game.end_time = None
        game.save()
        
        # Reset all cards
        for deck in game.decks.all():
            deck.cards.all().update(revealed=False)
        
        # Add a system message
        create_system_message(
            game,
            "Game has been reset by the host.",
            "warning"
        )
    
    messages.success(request, "Game has been reset to setup status")
    return redirect('game_admin', game_id=game.id)

@login_required
def game_admin_toggle_card(request, game_id, card_id):
    """Toggle the reveal status of a card"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure user is host of this game
    try:
        player = Player.objects.get(user=request.user, game=game, is_host=True)
    except Player.DoesNotExist:
        messages.error(request, "Only the host can toggle card reveal status")
        return redirect('game_detail', game_id=game.id)
    
    # Try to find the card, either in the game deck or in a player's hand
    try:
        card = Card.objects.get(
            id=card_id,
            deck__game=game
        )
    except Card.DoesNotExist:
        try:
            card = Card.objects.get(
                id=card_id,
                in_hands__game=game
            )
        except Card.DoesNotExist:
            messages.error(request, f"Card with ID {card_id} not found in game {game.title}")
            return redirect('game_admin', game_id=game.id)
    
    
    # Toggle the card's revealed status
    card.revealed = not card.revealed
    card.save()
    
    # Add a system message
    action = "revealed" if card.revealed else "hidden"
    create_system_message(
        game,
        f"Card '{card.title}' has been {action} by the host",
        "info"
    )
    
    messages.success(request, f"Card '{card.title}' has been {action}")
    
    # Return to the previous page
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('game_admin', game_id=game.id)

@login_required
def game_admin_make_host(request, game_id, player_id):
    """Make another player the host"""
    game = get_object_or_404(Game, id=game_id)
    target_player = get_object_or_404(Player, id=player_id, game=game)
    
    # Ensure user is host of this game
    try:
        current_host = Player.objects.get(user=request.user, game=game, is_host=True)
    except Player.DoesNotExist:
        messages.error(request, "Only the host can transfer host status")
        return redirect('game_detail', game_id=game.id)
    
    # Ensure target player isn't already host
    if target_player.is_host:
        messages.warning(request, f"{target_player.character_name} is already the host")
        return redirect('game_admin', game_id=game.id)
    
    # Transfer host status
    with transaction.atomic():
        current_host.is_host = False
        current_host.save()
        
        target_player.is_host = True
        target_player.save()
        
        # Add a system message
        create_system_message(
            game,
            f"{current_host.character_name} has transferred host status to {target_player.character_name}.",
            "info"
        )
    
    messages.success(request, f"{target_player.character_name} is now the host")
    return redirect('game_detail', game_id=game.id)

@login_required
def game_admin_player_cards(request, game_id, player_id):
    """Manage cards for a specific player"""
    game = get_object_or_404(Game, id=game_id)
    target_player = get_object_or_404(Player, id=player_id, game=game)
    
    # Ensure user is host of this game
    try:
        player = Player.objects.get(user=request.user, game=game, is_host=True)
    except Player.DoesNotExist:
        messages.error(request, "Only the host can manage player cards")
        return redirect('message_view', game_id=game.id)
    
    # Get the player's hand
    hand = get_object_or_404(Hand, player=target_player, game=game)
    
    # Handle form submission
    if request.method == 'POST':
        action = request.POST.get('action')
        card_ids = request.POST.getlist('card_ids')
        
        if action and card_ids:
            if action == 'add':
                # Add cards to hand
                for card_id in card_ids:
                    card = get_object_or_404(Card, id=card_id, deck__game=game)
                    hand.cards.add(card)
                messages.success(request, f"Added {len(card_ids)} card(s) to {target_player.character_name}'s hand")
            
            elif action == 'remove':
                # Remove cards from hand
                for card_id in card_ids:
                    card = get_object_or_404(Card, id=card_id)
                    hand.cards.remove(card)
                messages.success(request, f"Removed {len(card_ids)} card(s) from {target_player.character_name}'s hand")
    
    # Get all cards for this game
    game_cards = Card.objects.filter(deck__game=game)
    
    # Get player's current cards
    player_cards = hand.cards.all()
    
    # Get available cards (cards not in player's hand)
    available_cards = game_cards.exclude(id__in=player_cards.values_list('id', flat=True))
    
    context = {
        'game': game,
        'player': player,
        'target_player': target_player,
        'hand': hand,
        'player_cards': player_cards,
        'available_cards': available_cards,
    }
    
    return render(request, 'game/game_admin_player_cards.html', context)

@login_required
def game_admin_deal_cards(request, game_id):
    """Automatically deal cards to players"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure user is host of this game
    try:
        player = Player.objects.get(user=request.user, game=game, is_host=True)
    except Player.DoesNotExist:
        messages.error(request, "Only the host can deal cards")
        return redirect('message_view', game_id=game.id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action:
            # Get all players
            players = game.players.all()
            
            # Get game cards for the specified type
            if action == 'clues':
                cards = Card.objects.filter(deck__game=game, card_type='clue')
                
                if cards.exists():
                    import random
                    for p in players:
                        hand = Hand.objects.get(player=p, game=game)
                        # Assign 1-2 clue cards to each player
                        available_cards = cards.exclude(in_hands__isnull=False)
                        if available_cards.exists():
                            num_cards = min(2, available_cards.count())
                            cards_to_deal = random.sample(list(available_cards), num_cards)
                            for card in cards_to_deal:
                                hand.cards.add(card)
                    
                    messages.success(request, "Clue cards have been dealt to all players")
                else:
                    messages.warning(request, "No clue cards available")
            
            elif action == 'characters':
                cards = Card.objects.filter(deck__game=game, card_type='character')
                
                if cards.exists():
                    # Try to match characters to player names
                    for p in players:
                        if not p.character_card:
                            # Try to find a matching character card
                            matching_card = None
                            for card in cards:
                                if p.character_name and card.title and p.character_name.lower() in card.title.lower():
                                    matching_card = card
                                    break
                            
                            # If no match, assign randomly
                            if not matching_card and cards.filter(assigned_to__isnull=True).exists():
                                import random
                                available_cards = cards.filter(assigned_to__isnull=True)
                                matching_card = random.choice(available_cards)
                            
                            if matching_card:
                                p.character_card = matching_card
                                p.save()
                    
                    messages.success(request, "Character cards have been assigned to players")
                else:
                    messages.warning(request, "No character cards available")
            
            elif action == 'locations':
                cards = Card.objects.filter(deck__game=game, card_type='location')
                
                if cards.exists():
                    # Deal one location card to each player
                    import random
                    available_cards = list(cards.exclude(in_hands__isnull=False))
                    for i, p in enumerate(players):
                        if i < len(available_cards):
                            hand = Hand.objects.get(player=p, game=game)
                            hand.cards.add(available_cards[i])
                    
                    messages.success(request, "Location cards have been dealt to players")
                else:
                    messages.warning(request, "No location cards available")
            
            elif action == 'suspects':
                cards = Card.objects.filter(deck__game=game, card_type='suspect')
                
                if cards.exists():
                    # Deal one suspect card to each player
                    import random
                    available_cards = list(cards.exclude(in_hands__isnull=False))
                    for i, p in enumerate(players):
                        if i < len(available_cards):
                            hand = Hand.objects.get(player=p, game=game)
                            hand.cards.add(available_cards[i])
                    
                    messages.success(request, "Suspect cards have been dealt to players")
                else:
                    messages.warning(request, "No suspect cards available")
            
            elif action == 'motive':
                cards = Card.objects.filter(deck__game=game, card_type='motive')
                
                if cards.exists():
                    # Deal one motive card to a random player
                    import random
                    available_cards = list(cards.exclude(in_hands__isnull=False))
                    if available_cards and players.exists():
                        random_player = random.choice(players)
                        hand = Hand.objects.get(player=random_player, game=game)
                        hand.cards.add(available_cards[0])
                        
                        messages.success(request, f"Motive card has been dealt to {random_player.character_name}")
                    else:
                        messages.warning(request, "No motive cards available or no players to deal to")
                else:
                    messages.warning(request, "No motive cards available")
    
    return redirect('game_admin', game_id=game.id)

@login_required
def game_admin_reveal_card(request, game_id, card_id):
    """Reveal a card immediately"""
    game = get_object_or_404(Game, id=game_id)
    card = get_object_or_404(Card, id=card_id, deck__game=game)
    
    # Ensure user is host of this game
    try:
        player = Player.objects.get(user=request.user, game=game, is_host=True)
    except Player.DoesNotExist:
        messages.error(request, "Only the host can reveal cards")
        return redirect('message_view', game_id=game.id)
    
    # Skip if already revealed
    if card.revealed:
        messages.warning(request, f"Card '{card.title}' is already revealed")
        return redirect('game_admin', game_id=game.id)
    
    # Reveal the card
    card.revealed = True
    card.save()
    
    # Add a system message
    create_system_message(
        game,
        f"Card revealed by host: {card.title}",
        "success"
    )
    
    messages.success(request, f"Card '{card.title}' has been revealed")
    return redirect('game_admin', game_id=game.id)

@login_required
def game_admin_send_message(request, game_id):
    """Send a system message to all players"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure user is host of this game
    try:
        player = Player.objects.get(user=request.user, game=game, is_host=True)
    except Player.DoesNotExist:
        messages.error(request, "Only the host can send system messages")
        return redirect('message_view', game_id=game.id)
    
    if request.method == 'POST':
        message_content = request.POST.get('message_content', '').strip()
        
        if message_content:
            # Create the system message
            create_system_message(
                game,
                message_content,
                "info"
            )
            
            messages.success(request, "System message sent successfully")
        else:
            messages.error(request, "Message content cannot be empty")
    
    return redirect('game_admin', game_id=game.id)

@login_required
def game_messages(request, game_id):
    """Get messages after a specific ID"""
    game = get_object_or_404(Game, id=game_id)
    
    # Ensure user is part of this game
    try:
        player = Player.objects.get(user=request.user, game=game)
    except Player.DoesNotExist:
        return HttpResponseForbidden("You are not part of this game")
    
    # Get the last message ID from the request
    after_id = request.GET.get('after', 0)
    try:
        after_id = int(after_id)
    except ValueError:
        after_id = 0
    
    # Get messages after the specified ID
    messages = Message.objects.filter(
        game=game,
        id__gt=after_id
    ).order_by('timestamp')
    
    # Format messages for JSON response
    message_list = []
    for msg in messages:
        message_data = {
            'id': msg.id,
            'type': 'system' if msg.is_system_message else 'sent' if msg.sender == player else 'received',
            'isDirect': bool(msg.recipient),
            'content': msg.content,
            'time': msg.timestamp.strftime('%H:%M')
        }
        
        if not msg.is_system_message:
            message_data['sender'] = {
                'name': msg.sender.character_name,
                'color': msg.sender.color
            }
            if msg.recipient:
                message_data['recipient'] = msg.recipient.character_name
        
        if msg.image:
            message_data['image'] = {
                'url': msg.image.url,
                'detailUrl': reverse('message_detail', args=[game.id, msg.id])
            }
        
        message_list.append(message_data)
    
    return JsonResponse({'messages': message_list})

def create_system_message(game, content, system_type=None):
    """
    Create a system message with optional type (alert, success, info, warning)
    """
    message = Message.objects.create(
        game=game,
        content=content,
        is_system_message=True,
        system_type=system_type
    )
    return message

def start_game(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    if request.user != game.host:
        return JsonResponse({'error': 'Only the host can start the game'}, status=403)
    
    if game.status != 'setup':
        return JsonResponse({'error': 'Game is not in setup mode'}, status=400)
    
    game.status = 'in_progress'
    game.start_time = timezone.now()
    game.save()
    
    create_system_message(game, "The game has started!", "success")
    return JsonResponse({'status': 'success'})

def end_game(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    if request.user != game.host:
        return JsonResponse({'error': 'Only the host can end the game'}, status=403)
    
    if game.status != 'in_progress':
        return JsonResponse({'error': 'Game is not in progress'}, status=400)
    
    game.status = 'finished'
    game.end_time = timezone.now()
    game.save()
    
    create_system_message(game, "The game has ended!", "info")
    return JsonResponse({'status': 'success'})

def reset_game(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    if request.user != game.host:
        return JsonResponse({'error': 'Only the host can reset the game'}, status=403)
    
    game.status = 'setup'
    game.start_time = None
    game.end_time = None
    game.save()
    
    create_system_message(game, "The game has been reset to setup mode.", "warning")
    return JsonResponse({'status': 'success'})

def player_joined(game, player):
    create_system_message(game, f"{player.character_name} has joined the game!", "info")

def player_left(game, player):
    create_system_message(game, f"{player.character_name} has left the game.", "alert")

def card_revealed(game, card):
    create_system_message(game, f"The card '{card.title}' has been revealed!", "success")

def card_hidden(game, card):
    create_system_message(game, f"The card '{card.title}' has been hidden.", "warning")

@login_required
def game_admin_clear_messages(request, game_id):
    """Clear all messages in a game"""
    game = get_object_or_404(Game, id=game_id)
    
    # Check if user is the host
    if not game.is_host(request.user):
        return JsonResponse({'error': 'Only the host can clear messages'}, status=403)
    
    # Delete all messages
    game.messages.all().delete()
    
    return JsonResponse({'status': 'success'})

@login_required
def log_error(request):
    """Log client-side errors"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.error(
                f"Client Error: {data.get('error')}\n"
                f"Context: {data.get('context')}\n"
                f"Stack: {data.get('stack')}\n"
                f"URL: {data.get('context', {}).get('url')}\n"
                f"User Agent: {data.get('context', {}).get('userAgent')}"
            )
            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError:
            logger.error("Invalid JSON in log_error request")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.exception("Error in log_error view")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
