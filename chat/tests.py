from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import ChatMessage


class ChatViewTests(TestCase):
    def test_chat_page_requires_login(self):
        response = self.client.get(reverse("dietobot-chat"))

        self.assertEqual(response.status_code, 302)

    def test_chat_post_saves_messages_and_redirects(self):
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
        workflow.assert_called_once_with(user, "I am 30.")
        self.assertEqual(ChatMessage.objects.filter(user=user).count(), 2)

    def test_chat_get_renders_conversation(self):
        user = get_user_model().objects.create_user(username="mira", password="pw")
        self.client.login(username="mira", password="pw")
        ChatMessage.objects.create(user=user, role=ChatMessage.Role.USER, content="Hello")
        ChatMessage.objects.create(user=user, role=ChatMessage.Role.ASSISTANT, content="Hi there!")

        response = self.client.get(reverse("dietobot-chat"))

        self.assertContains(response, "Hello")
        self.assertContains(response, "Hi there!")
