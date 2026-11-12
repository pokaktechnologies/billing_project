from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from core import settings
from accounts.services.pagination import api_response, paginate_response
from ..models import OfferLetter, StatusChoices, OfferLetterAnnexure
from ..serializers import (
    OfferLetterCreateSerializer,
    OfferLetterPatchSerializer,
    OfferLetterListSerializer,
    OfferLetterDetailSerializer,
    OfferLetterShareSerializer,
    OfferLetterAnnexureSerializer,
)
from ..filters import OfferLetterFilter


class OfferLetterListCreateAPIView(generics.ListCreateAPIView):
    permission_classes  = [IsAuthenticated]
    queryset            = OfferLetter.objects.select_related("created_by").all()
    filter_backends     = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class     = OfferLetterFilter
    search_fields       = ["candidate_name", "candidate_email", "job_title", "company_name"]
    ordering_fields     = ["created_at", "updated_at", "joining_date", "monthly_salary"]
    ordering            = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OfferLetterCreateSerializer
        return OfferLetterListSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return paginate_response(queryset, request, OfferLetterListSerializer)

    def create(self, request, *args, **kwargs):
        serializer = OfferLetterCreateSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            offer = serializer.save()
            return api_response(
                message="Offer letter created successfully.",
                data=OfferLetterDetailSerializer(offer).data,
            )
        return api_response(
            status="0",
            message="Validation failed.",
            data=serializer.errors,
        )


class OfferLetterDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]

    queryset = OfferLetter.objects.select_related(
        "created_by"
    ).prefetch_related(
        "sections__subtitles__points"
    ).all()

    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return OfferLetterPatchSerializer
        return OfferLetterDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        offer = self.get_object()
        return api_response(
            data=OfferLetterDetailSerializer(offer).data
        )

    def partial_update(self, request, *args, **kwargs):
        offer = self.get_object()

        if offer.status == "accepted":
            return api_response(
                status="0",
                message="Cannot modify an accepted offer letter.",
            )

        serializer = OfferLetterPatchSerializer(
            offer, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            updated = serializer.save()
            return api_response(
                message="Offer letter updated successfully.",
                data=OfferLetterDetailSerializer(updated).data,
            )
        return api_response(
            status="0",
            message="Validation failed.",
            data=serializer.errors,
        )

    def destroy(self, request, *args, **kwargs):
        offer = self.get_object()
        offer.delete()
        return api_response(message="Offer letter deleted successfully.")


class OfferLetterShareAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        offer = get_object_or_404(
            OfferLetter,
            pk=pk
        )

        serializer = OfferLetterShareSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return api_response(
                status="0",
                message="Validation failed.",
                data=serializer.errors
            )

        email = serializer.validated_data["email"]
        subject = serializer.validated_data["subject"]
        message = serializer.validated_data.get(
            "message",
            ""
        )
        pdf = serializer.validated_data["pdf"]

        try:
            mail = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )

            mail.attach(
                pdf.name,
                pdf.read(),
                "application/pdf"
            )

            mail.send(
                fail_silently=False
            )

            offer.status = StatusChoices.SENT
            offer.save(update_fields=["status", "updated_at"])
            
            return api_response(
                message="Offer letter sent successfully.",
                data={
                    "offer_letter_id": offer.id,
                    "email": email,
                }
            )

        except Exception as e:
            return api_response(
                status="0",
                message="Failed to send offer letter.",
                data={
                    "error": str(e)
                }
            )


class OfferLetterAnnexureAPIView(APIView):
    """
    Dedicated endpoint for managing the standalone Annexure for an Offer Letter.
    GET  /hr/offer-letters/<pk>/annexure/ -> Fetch saved annexure data or Status=0 if none
    POST /hr/offer-letters/<pk>/annexure/ -> Create or update the annexure data
    DELETE /hr/offer-letters/<pk>/annexure/ -> Delete the annexure data
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        offer = get_object_or_404(OfferLetter, pk=pk)
        try:
            annexure = offer.annexure
            serializer = OfferLetterAnnexureSerializer(annexure)
            return api_response(
                message="Annexure fetched successfully.",
                data=serializer.data
            )
        except OfferLetterAnnexure.DoesNotExist:
            return api_response(
                status="0",
                message="No annexure found for this offer letter.",
                data=None
            )

    def post(self, request, pk):
        offer = get_object_or_404(OfferLetter, pk=pk)
        annexure, _ = OfferLetterAnnexure.objects.get_or_create(
            offer_letter=offer,
            defaults={
                "title": request.data.get("title", "Offer Letter Annexures"),
                "pages": request.data.get("pages", []),
                "created_by": request.user,
            }
        )

        serializer = OfferLetterAnnexureSerializer(
            annexure,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            saved_annexure = serializer.save(
                created_by=request.user if not annexure.created_by else annexure.created_by
            )
            return api_response(
                message="Annexure saved successfully.",
                data=OfferLetterAnnexureSerializer(saved_annexure).data
            )

        return api_response(
            status="0",
            message="Validation failed.",
            data=serializer.errors
        )

    def delete(self, request, pk):
        offer = get_object_or_404(OfferLetter, pk=pk)
        try:
            offer.annexure.delete()
            return api_response(message="Annexure deleted successfully.")
        except OfferLetterAnnexure.DoesNotExist:
            return api_response(
                status="0",
                message="No annexure found to delete."
            )


