from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ai.workflows.orchestrator import run_chat_workflow

from .models import ChatMessage


def conversation_for(user):
    """Return this user's chat history in the shape the workflow expects."""

    return [
        {"role": message.role, "content": message.content}
        for message in ChatMessage.objects.filter(user=user)
    ]


@login_required
def chat(request):
    """Show the chat and process one message at a time."""

    if request.method == 'POST':
        message = request.POST.get('message', '').strip()

        if message:
            ChatMessage.objects.create(
                user=request.user,
                role=ChatMessage.Role.USER,
                content=message,
            )
            reply = run_chat_workflow(
                message,
                conversation=conversation_for(request.user),
            )["reply"]
            ChatMessage.objects.create(
                user=request.user,
                role=ChatMessage.Role.ASSISTANT,
                content=reply,
            )

        return redirect('dietobot-chat')

    messages = ChatMessage.objects.filter(user=request.user)
    context = {"messages": messages}

    return render(request, 'chat/chat.html', context)
