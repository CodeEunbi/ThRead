from django.conf import settings

from chat.serializers import MessageSerializer
from openai import OpenAI
from openai import OpenAIError


from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView


# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Conversation, PersonaPrompt
from books.models import Book
from .models import Message
import json

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


# import os
# from dotenv import load_dotenv

# load_dotenv()
# print(os.getenv("OPENAI_API_KEY"))

# Create your views here.
# @csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_api_view(request):
    # 🔥 DRF에서는 request.data를 써야 함
    book_id = request.data.get("bookId")
    question = request.data.get("question")

    print("🔥 request.data:", request.data)  # 디버그용

    if not book_id or not question:
        return Response(
            {"error": "bookId와 question이 필요합니다."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        return Response(
            {"error": "책을 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND
        )

    persona, _ = PersonaPrompt.objects.get_or_create(
        book=book,
        defaults={
            'prompt': f"당신은 '{book.title}'의 작가입니다. 이 책에 대해 사용자에게 안내하세요."
        }
    )

    conversation, _ = Conversation.objects.get_or_create(
        user=request.user,
        persona=persona,
    )

    prompt = f"""
당신은 이 책의 작가입니다.
책 제목: {book.title}
저자: {book.author}
사용자 질문: {question}
3줄 이내로 답변하세요.
"""

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 책의 작가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.1,
        )

        answer = response.choices[0].message.content.strip()

        Message.objects.create(conversation=conversation, is_user=True, content=question)
        Message.objects.create(conversation=conversation, is_user=False, content=answer)

        return Response({
            "answer": answer,
            "conversation_id": conversation.id
        })

    except OpenAIError as e:
        return Response({"error": str(e)}, status=500)


    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_or_create_conversation(request):
    user = request.user
    book_id = request.data.get('book_id')

    if not book_id:
        return Response({'error': 'book_id가 필요합니다.'}, status=400)

    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        return Response({'error': '해당 책을 찾을 수 없습니다.'}, status=404)

    persona = PersonaPrompt.objects.filter(book=book).first()
    if not persona:
        return Response({'error': '해당 책에 대한 페르소나가 없습니다.'}, status=404)

    conversation, created = Conversation.objects.get_or_create(
        user=user,
        persona=persona
    )

    messages = Message.objects.filter(conversation=conversation).order_by('timestamp')
    serialized = MessageSerializer(messages, many=True)

    return Response({
        'conversation_id': conversation.id,
        'messages': serialized.data,
        'created': created
    })
# def conversation_list_create(request):
#   if request.method == 'POST':
#       body = json.loads(request.body)
#       book_id = body.get('book_id')

#       try:
#           # 책이 존재하는지 확인
#           book = Book.objects.get(id=book_id)
#       except Book.DoesNotExist:
#           return JsonResponse({'error': 'Book not found'}, status=404)

#       # 해당 책의 persona가 없다면 자동 생성
#       persona, created = PersonaPrompt.objects.get_or_create(
#           book=book,
#           defaults={
#               'prompt': f"당신은 '{book.title}'의 저자입니다. 이 책에 대해 사용자에게 안내하세요."
#           }
#       )

#       # 대화 생성
#       conversation = Conversation.objects.create(user=request.user, persona=persona)
#       return JsonResponse({'id': conversation.id}, status=201)


def conversation_detail(request, pk):
    try:
        conversation = Conversation.objects.get(pk=pk, user=request.user)
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found'}, status=404)

    messages = conversation.messages.all().order_by('timestamp')
    data = {
        'id': conversation.id,
        'title': conversation.title or conversation.persona.book.title,
        'messages': [
            {
                'id': m.id,
                'is_user': m.is_user,
                'content': m.content,
                'timestamp': m.timestamp,
            }
            for m in messages
        ]
    }
    return JsonResponse(data)


@csrf_exempt
def add_message(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        conversation = Conversation.objects.get(pk=pk, user=request.user)
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found'}, status=404)

    body = json.loads(request.body)
    question = body.get('message')

    # 1. 유저 메시지 저장
    from .models import Message
    Message.objects.create(conversation=conversation, is_user=True, content=question)

    # 2. AI 응답 생성 (임시 응답으로 대체)
    ai_response = f"이건 '{question}'에 대한 임시 응답이야 :)"
    Message.objects.create(conversation=conversation, is_user=False, content=ai_response)

    return JsonResponse({'response': ai_response})


@csrf_exempt
def ensure_persona(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST 요청만 지원합니다.'}, status=405)

    try:
        data = json.loads(request.body)
        book_id = data.get("book_id")
        if not book_id:
            return JsonResponse({'error': 'book_id가 필요합니다.'}, status=400)

        book = Book.objects.get(id=book_id)

        persona, created = PersonaPrompt.objects.get_or_create(
            book=book,
            defaults={
                'prompt': f"당신은 '{book.title}'의 작가입니다. 이 책에 대해 사용자에게 안내하세요."
            }
        )

        return JsonResponse({
            'persona_id': persona.id,
            'created': created,
            'prompt': persona.prompt
        })

    except Book.DoesNotExist:
        return JsonResponse({'error': '책을 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)