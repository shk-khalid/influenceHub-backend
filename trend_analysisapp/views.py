from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Trend
from .serializers import TrendSerializer
from .utils import fetch_and_update_trends
from celery.worker import request

class TrendAnalysisView(APIView):
    def get(self, request):
        search_query = request.query_params.get('search', None)
        category_filter = request.query_params.get('category', None)
        region_filter = request.query_params.get('region', None)
        
        trends = Trend.objects.all()
        
        if search_query:
            trends = trends.filter(name__icontains=search_query)
        if category_filter:
            trends = trends.filter(category=category_filter)
        if region_filter:
            trends = trends.filter(region=region_filter)
            
        serializer = TrendSerializer(trends, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RefreshTrendView(APIView):
    def get(self, request):
        try:
            fetch_and_update_trends()
            return Response({'message': 'Trends updated successfully!'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)