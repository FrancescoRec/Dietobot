from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import ChatMessage


class ChatViewTests(TestCase):
    def test_chat_page_requires_login(self):
        response = self.client.get(reverse("dietobot-chat"))

        self.assertEqual(response.status_code, 302)

    def test_chat_post_saves_and_renders_full_conversation(self):
        user = get_user_model().objects.create_user(username="avi", password="pw")
        self.client.login(username="avi", password="pw")

        with patch(
            "chat.views.run_chat_workflow",
            return_value={"reply": "Got it. Could you tell me your height?"},
        ) as workflow:
            response = self.client.post(
                reverse("dietobot-chat"),
                {"message": "I am 30."},
            )

        self.assertRedirects(response, reverse("dietobot-chat"))
        workflow.assert_called_once_with("I am 30.")
        self.assertEqual(ChatMessage.objects.filter(user=user).count(), 2)

        response = self.client.get(reverse("dietobot-chat"))

        self.assertContains(response, "I am 30.")
        self.assertContains(response, "Got it. Could you tell me your height?")
        self.assertContains(response, "message-user")
        self.assertContains(response, "message-bot")
