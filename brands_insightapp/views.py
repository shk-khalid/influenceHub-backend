from rest_framework.views import APIView
from rest_framework.response import Response   
from rest_framework import status
from .models import Brand
from .serializers import BrandListSerializer, BrandDetailSerializer

class BrandListView(APIView):
    def get(self, request):
        brands = Brand.objects.all()
        serializer = BrandListSerializer(brands, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class BrandDetailListView(APIView):
    def get(self, request, pk):
        try:
            brand = Brand.objects.get(id=pk)
        except Brand.DoesNotExist:
            return Response({"error": "Brand not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = BrandDetailSerializer(brand)
        return Response(serializer.data, status=status.HTTP_200_OK)