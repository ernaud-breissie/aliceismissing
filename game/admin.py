from django.contrib import admin
from .models import Game, Player, Card, Deck, Hand, Message

admin.site.register(Game)
admin.site.register(Player)
admin.site.register(Card)
admin.site.register(Deck)
admin.site.register(Hand)
admin.site.register(Message)
