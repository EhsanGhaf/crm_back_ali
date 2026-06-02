from django.urls import path
from .views import *

urlpatterns = [

    path('list/', TicketListAPIView.as_view(), name='ticket-list'),
    path('submit/', SubmitTicketAPIView.as_view(), name='submit-ticket'),
    path('customer/<str:identifier>/', CustomerProfileAPIView.as_view(), name='customer-profile'),
    # Seeing The Ticket Detail (GET)
    path('<int:ticket_id>/detail/', TicketDetailAPIView.as_view(), name='ticket-detail'),

    # Sending Note (POST)
    path('<int:ticket_id>/reply/', TicketReplyAPIView.as_view(), name='ticket-reply'),

    path('<int:ticket_id>/dynamic-data/', TicketDynamicDataAPIView.as_view(), name='ticket-dynamic-data'),

    path('<int:ticket_id>/state/', TicketStateUpdateAPIView.as_view(), name='ticket-state-update'),

    path('groups/',ZammadGroupAPIView.as_view(), name='zammad-groups'),

    path('resolution-codes/', ResolutionCodeListAPIView.as_view(), name='resolution-codes'),
    path('<int:ticket_id>/assign/', TicketAssignToMeAPIView.as_view()),
]