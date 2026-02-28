# core/base_view.py

from rest_framework.views import APIView
from .utils import set_current_user

class BaseAPIView(APIView):

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        if request.user and request.user.is_authenticated:
            set_current_user(request.user)




from rest_framework.generics import GenericAPIView

class BaseGenericAPIView(GenericAPIView):

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        if request.user and request.user.is_authenticated:
            set_current_user(request.user)



from rest_framework.viewsets import ModelViewSet

class BaseModelViewSet(ModelViewSet):

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        if request.user and request.user.is_authenticated:
            set_current_user(request.user)