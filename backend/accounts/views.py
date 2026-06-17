import json
import urllib.request

from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserAdminSerializer, UserSerializer

User = get_user_model()


class UserListCreateView(ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = UserAdminSerializer

    def get_queryset(self):
        return User.objects.order_by("username")


class UserDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = UserAdminSerializer

    def get_queryset(self):
        return User.objects.order_by("username")

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            requested_active = request.data.get("is_active", user.is_active)
            requested_staff = request.data.get("is_staff", user.is_staff)
            if requested_active is False or requested_staff is False:
                return Response(
                    {"detail": "You cannot deactivate or remove administrator access from your own account."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response({"detail": "You cannot delete your own account."}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password")
        if "@" in username:
            user_by_email = User.objects.filter(Q(email__iexact=username)).first()
            username = user_by_email.username if user_by_email else username
        user = authenticate(username=username, password=password)
        if not user or not user.is_active:
            return Response({"detail": "Invalid username or password."}, status=status.HTTP_400_BAD_REQUEST)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        access_token = request.data.get("access_token", "").strip()
        if not access_token:
            return Response({"detail": "access_token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            req = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                user_info = json.loads(resp.read())
        except Exception:
            return Response({"detail": "Invalid or expired Google token."}, status=status.HTTP_400_BAD_REQUEST)

        email = user_info.get("email", "").lower()
        if not email:
            return Response({"detail": "Google account has no email address."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if user is None:
            return Response({"detail": "Ask an administrator to create your account first."}, status=status.HTTP_403_FORBIDDEN)
        if not user.is_active:
            return Response({"detail": "This account is inactive."}, status=status.HTTP_403_FORBIDDEN)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data}, status=status.HTTP_200_OK)
