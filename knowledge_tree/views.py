from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets
from .models import CategoryNode
from .serializers import CategoryNodeSerializer , CategoryNodeAdminSerializer
from django.db.models import Q
# Create your views here.

class KnowledgeTreeAPIView(APIView):
    def get(self, request):
        root_nodes = CategoryNode.objects.filter(
            parent__isnull=True,
            is_active=True,
        ).prefetch_related('children')

        serializer = CategoryNodeSerializer(root_nodes, many=True)

        return Response({
            'message': 'درخت دانش با موفقیت دریافت شد.',
            'data': serializer.data,
        })


class KnowledgeTreeSearchAPIView(APIView):
    """
    This Api Get a Node And Return everything With it
    """

    def get(self, request):
        query = request.GET.get('q', '').strip()

        if not query:
            return Response(
                {"message": "لطفاً عبارتی را برای جستجو وارد کنید.", "data": []},
                status=200
            )

        results = CategoryNode.objects.filter(
            Q(name__icontains=query) | Q(search_keywords__icontains=query),
            is_active=True
        ).distinct()

        serializer = CategoryNodeSerializer(results, many=True)

        return Response({
            "message": f"نتایج جستجو برای '{query}'",
            "data": serializer.data
        })


class CategoryNodeViewSet(viewsets.ModelViewSet):

    queryset = CategoryNode.objects.all()

    serializer_class = CategoryNodeAdminSerializer