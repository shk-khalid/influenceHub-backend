from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Trend
from .serializers import TrendSerializer
from .utils import fetch_and_update_trends

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
    
    def post(self):
        try:
            fetch_and_update_trends()

            trends = Trend.objects.all()
            serializer = TrendSerializer(trends, many=True)
            return Response({
                "message": "Trends successfully refreshed.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "error": "Failed to refresh trends.",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)