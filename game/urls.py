from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='game/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    
    # Game management URLs
    path('', views.home, name='home'),
    path('new-game/', views.new_game, name='new_game'),
    path('join-game/', views.join_game, name='join_game'),
    path('join-game/<str:join_code>/', views.join_game_with_code, name='join_game_with_code'),
    
    # Game play URLs
    path('game/<int:game_id>/', views.game_detail, name='game_detail'),  # Main view for messages
    path('game/<int:game_id>/info/', views.game_info, name='game_info'),  # Game information view
    path('game/<int:game_id>/setup/', views.game_setup, name='game_setup'),
    path('game/<int:game_id>/start/', views.start_game, name='start_game'),
    path('game/<int:game_id>/end/', views.end_game, name='end_game'),
    
    # Messaging URLs
    path('game/<int:game_id>/messages/send/', views.send_message, name='send_message'),
    path('game/<int:game_id>/messages/<int:message_id>/', views.message_detail, name='message_detail'),
    path('game/<int:game_id>/messages/', views.game_messages, name='game_messages'),  # Added URL for fetching messages
    
    # Card management URLs
    path('game/<int:game_id>/hand/', views.player_hand, name='player_hand'),
    path('game/<int:game_id>/card/<int:card_id>/', views.card_detail, name='card_detail'),
    path('game/<int:game_id>/card/<int:card_id>/reveal/', views.reveal_card, name='reveal_card'),
    
    # Character selection
    path('game/<int:game_id>/select-character/', views.select_character, name='select_character'),
    path('game/<int:game_id>/assign-color/', views.assign_color, name='assign_color'),
    
    # Timer and status updates
    path('game/<int:game_id>/timer/', views.game_timer, name='game_timer'),
    path('game/<int:game_id>/status/', views.game_status, name='game_status'),
    
    # In-game admin interface
    path('game/<int:game_id>/admin/', views.game_admin, name='game_admin'),
    path('game/<int:game_id>/admin/reset/', views.game_admin_reset, name='game_admin_reset'),
    path('game/<int:game_id>/admin/make-host/<int:player_id>/', views.game_admin_make_host, name='game_admin_make_host'),
    path('game/<int:game_id>/admin/player-cards/<int:player_id>/', views.game_admin_player_cards, name='game_admin_player_cards'),
    path('game/<int:game_id>/admin/deal-cards/', views.game_admin_deal_cards, name='game_admin_deal_cards'),
    path('game/<int:game_id>/admin/reveal-card/<int:card_id>/', views.game_admin_reveal_card, name='game_admin_reveal_card'),
    path('game/<int:game_id>/admin/send-message/', views.game_admin_send_message, name='game_admin_send_message'),
    path('game/<int:game_id>/admin/toggle-card/<int:card_id>/', views.game_admin_toggle_card, name='game_admin_toggle_card'),
    path('game/<int:game_id>/admin/clear-messages/', views.game_admin_clear_messages, name='game_admin_clear_messages'),
    path('log-error/', views.log_error, name='log_error_client'),
]

