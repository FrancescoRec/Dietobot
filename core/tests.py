from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_requires_login(self):
        response = self.client.get(reverse("home"))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('home')}")

    def test_home_is_logo_and_chat_call_to_action(self):
        user = get_user_model().objects.create_user(username="mira", password="pw")
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertContains(response, "images/logo.gif")
        self.assertContains(response, "Go to chat")
        self.assertContains(response, "Log out")
        self.assertNotContains(response, 'class="site-header"')
