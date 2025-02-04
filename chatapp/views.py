from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import ChatMessage
from .serializers import ChatMessageSerializer
import google.generativeai as genai
import os

class ChatViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-pro')
        
    @action(detail=False, methods=['post'])
    def send_message(self, request):
        session_id = request.data.get('session_id')
        message = request.data.get('message')
        
        # Save user message
        user_message = ChatMessage.objects.create(
            text=message,
            sender='user',
            session_id=session_id
        )
        
        try:
            # Get chat history with more specific context
            chat = self.model.start_chat(history=[
                {
                    "role": "user",
                    "parts": """You are an AI customer support specialist for NoxInfluencer, a social media analytics and influencer marketing platform. 
                    
                    IMPORTANT RULES:
                    1. ONLY answer questions related to:
                       - Social media analytics
                       - Influencer marketing
                       - Content creator strategies
                       - Social media metrics and KPIs
                       - Influencer collaboration
                       - Social media platform features
                    
                    2. For ANY question outside these topics, respond with:
                       "I apologize, but I can only assist with questions related to influencer marketing, social media analytics, and content creation. Please feel free to ask me about those topics!"
                    
                    3. Keep responses concise, professional, and focused on NoxInfluencer's features.
                    
                    4. Use specific examples related to social media platforms (YouTube, Instagram, TikTok, etc.).
                    
                    Remember: You are a specialist in influencer marketing and social media analytics ONLY."""
                },
                {
                    "role": "model",
                    "parts": "I understand my role as a specialized AI support agent for NoxInfluencer. I will strictly focus on influencer marketing, social media analytics, and content creation topics while politely deflecting unrelated questions."
                }
            ])
            
            # Get bot response
            response = chat.send_message(message)
            bot_message = ChatMessage.objects.create(
                text=response.text,
                sender='bot',
                session_id=session_id
            )
            
            return Response({
                'user_message': ChatMessageSerializer(user_message).data,
                'bot_message': ChatMessageSerializer(bot_message).data
            })
            
        except Exception as e:
            error_message = "I apologize, but I'm having trouble connecting right now. Please try again later."
            bot_message = ChatMessage.objects.create(
                text=error_message,
                sender='bot',
                session_id=session_id
            )
            return Response({
                'user_message': ChatMessageSerializer(user_message).data,
                'bot_message': ChatMessageSerializer(bot_message).data
            })