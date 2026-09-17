from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ai.workflows.orchestrator import run_chat_workflow


@login_required
def chat(request):
    """Show the chat and process one message at a time."""

    context = {}

    if request.method == 'POST':
        message = request.POST.get('message', '').strip()

        if message:
            context['message'] = message
            context.update(run_chat_workflow(message))

    return render(request, 'chat/chat.html', context)
