# Views: Health, Register, Login, KB query with pagination, Admin usage summary
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import ApiKeyAuthentication
from .models import KBEntry, QueryLog
from .permissions import IsAdminUser
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    KBEntrySerializer,
    KBQuerySerializer,
    TopSearchTermSerializer,
)

PAGE_SIZE_DEFAULT = 5
PAGE_SIZE_MAX     = 20


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


# ─── GET /api/health/ ────────────────────────────────────────────────────────

class HealthView(APIView):
    authentication_classes = []
    permission_classes     = []

    def get(self, request):
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


# ─── POST /api/auth/register/ ────────────────────────────────────────────────

class RegisterView(APIView):
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user = User.objects.create_user(
            username=data['username'],
            password=data['password'],
            email=data['email'],
        )

        company = user.company
        company.company_name = data['company_name']
        company.save(update_fields=['company_name'])

        return Response(
            {
                'username':     user.username,
                'company_name': company.company_name,
                'api_key':      company.api_key,
                'role':         company.role,
                'access':       get_tokens_for_user(user),
            },
            status=status.HTTP_201_CREATED,
        )


# ─── POST /api/auth/login/ ───────────────────────────────────────────────────

class LoginView(APIView):
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user = authenticate(request, username=data['username'], password=data['password'])

        if user is None:
            return Response(
                {'detail': 'Invalid username or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        company = user.company

        return Response(
            {
                'access':       get_tokens_for_user(user),
                'username':     user.username,
                'company_name': company.company_name,
                'api_key':      company.api_key,
                'role':         company.role,
            },
            status=status.HTTP_200_OK,
        )


# ─── POST /api/kb/query/ ─────────────────────────────────────────────────────

class KBQueryView(APIView):
    authentication_classes = [ApiKeyAuthentication]

    def post(self, request):
        serializer = KBQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        search_term = serializer.validated_data['search']
        company     = request.user.company

        try:
            page      = max(1, int(request.query_params.get('page', 1)))
            page_size = min(int(request.query_params.get('page_size', PAGE_SIZE_DEFAULT)), PAGE_SIZE_MAX)
        except (ValueError, TypeError):
            page, page_size = 1, PAGE_SIZE_DEFAULT

        with transaction.atomic():
            entries = KBEntry.objects.filter(
                Q(question__icontains=search_term) |
                Q(answer__icontains=search_term)
            )
            count = entries.count()
            QueryLog.objects.create(
                company=company,
                search_term=search_term,
                results_count=count,
            )

        start   = (page - 1) * page_size
        page_qs = entries[start:start + page_size]

        return Response(
            {
                'search':      search_term,
                'count':       count,
                'page':        page,
                'page_size':   page_size,
                'total_pages': max(1, -(-count // page_size)),
                'results':     KBEntrySerializer(page_qs, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


# ─── GET /api/admin/usage-summary/ ───────────────────────────────────────────

class AdminUsageSummaryView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total_queries    = QueryLog.objects.aggregate(total=Count('id'))['total']
        active_companies = QueryLog.objects.values('company').distinct().count()
        top_terms        = (
            QueryLog.objects
            .values('search_term')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        return Response(
            {
                'total_queries':    total_queries,
                'active_companies': active_companies,
                'top_search_terms': TopSearchTermSerializer(top_terms, many=True).data,
            },
            status=status.HTTP_200_OK,
        )
