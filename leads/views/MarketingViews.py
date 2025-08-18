from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.utils.timezone import make_aware
from django.utils.dateparse import parse_date
from datetime import datetime, date
from django.db.models import Q

from accounts.permissions import HasModulePermission

from ..models import *
from ..serializers.MarketingSerializers import *

class LocationtView(APIView):

    def get(self, request):
        locations = Location.objects.all()
        serializer = LocationSerializer(locations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = LocationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class LocationtDetailView(APIView):

    def get(self, request, pk):
        try:
            location = Location.objects.get(pk=pk)
        except Location.DoesNotExist:
            return Response({'error': 'Location not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = LocationSerializer(location)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        try:
            location = Location.objects.get(pk=pk)
        except Location.DoesNotExist:
            return Response({'error': 'Location not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = LocationSerializer(location, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def delete(self, request, pk):
        try:
            location = Location.objects.get(pk=pk)
        except Location.DoesNotExist:
            return Response({
                "status": "0",
                "message": "Location not found",
                "errors": f"Location with id {pk} does not exist"
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            location.delete()
            return Response({
                "status": "1",
                "message": "Location deleted successfully"
            }, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({
                "status": "0",
                "message": "Location deletion failed",
                "errors": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)




class SourceAPIView(APIView):
    def get(self, request):
        sources = Source.objects.all()
        serializer = SourceSerializer(sources, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = SourceSerializer(data=request.data)
        if serializer.is_valid():
            source = serializer.save()  # Use serializer’s create method
            return Response(SourceSerializer(source).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SourceDetailView(APIView):
    def get_object(self, pk, user):
        try:
            return Source.objects.get(pk=pk)
        except Source.DoesNotExist:
            return None
    def get(self, request, pk):
        source = self.get_object(pk, request.user)
        if not source:
            return Response({'error': 'Source not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = DisplaySourceSerializer(source)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        source = self.get_object(pk, request.user)
        if not source:
            return Response({'error': 'Source not found'}, status=status.HTTP_404_NOT_FOUND)        
        serializer = SourceSerializer(source, data=request.data, partial=True)
        if serializer.is_valid():
            source = serializer.save()  # Use serializer’s update method
            return Response(SourceSerializer(source).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        source = self.get_object(pk, request.user)
        if not source:
            return Response({
                "status": "0",
                "message": "Source not found",
                "errors": f"Source with id {pk} does not exist"
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            source.delete()
            return Response({
                "status": "1",
                "message": "Source deleted successfully"
            }, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({
                "status": "0",
                "message": "Source deletion failed",
                "errors": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)



class CategoryAPIView(APIView):
    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CategoryDetailAPIView(APIView):
    def get_object(self, pk):
        try:
            return Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return None

    def get(self, request, pk):
        category = self.get_object(pk)
        if not category:
            return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CategorySerializer(category)
        return Response(serializer.data)

    def patch(self, request, pk):
        category = self.get_object(pk)
        if not category:
            return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        category = self.get_object(pk)
        if not category:
            return Response({
                "status": "0",
                "message": "Category not found",
                "errors": f"Category with id {pk} does not exist"
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            category.delete()
            return Response({
                "status": "1",
                "message": "Category deleted successfully"
            }, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({
                "status": "0",
                "message": "Category deletion failed",
                "errors": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class MarketingReportAPIView(APIView):
    def get(self, request):
        # Query parameters
        source_id = request.query_params.get('source', None)
        category_id = request.query_params.get('category', None)
        location_id = request.query_params.get('location', None)
        salesperson_id = request.query_params.get('salesperson', None)
        from_date = request.query_params.get('from_date', None)
        to_date = request.query_params.get('to_date', None)

        # Start with all reports
        reports = MarketingReport.objects.all().order_by('-id')

        # Filter by source
        if source_id:
            reports = reports.filter(source_id=source_id)

            # Filter category only if it belongs to the source
            if category_id:
                reports = reports.filter(category_id=category_id, category__source_id=source_id)

        # Filter by location
        if location_id:
            reports = reports.filter(location_id=location_id)

        # Filter by salesperson
        if salesperson_id:
            reports = reports.filter(salesperson_id=salesperson_id)

        # Filter by date range
        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
                reports = reports.filter(date__gte=from_date_obj)
            except ValueError:
                return Response({
                    "status": "0",
                    "message": "Invalid from_date format",
                    "errors": "Expected YYYY-MM-DD"
                }, status=status.HTTP_400_BAD_REQUEST)

        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
                reports = reports.filter(date__lte=to_date_obj)
            except ValueError:
                return Response({
                    "status": "0",
                    "message": "Invalid to_date format",
                    "errors": "Expected YYYY-MM-DD"
                }, status=status.HTTP_400_BAD_REQUEST)

        # Serialize and return
        serializer = MarketingReportDisplaySerializer(reports, many=True)
        return Response({
            "status": "1",
            "message": "Reports retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    
    def post(self, request):
        serializer = MarketingReportSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            reports = serializer.save()
            # Return a list of serialized reports
            return Response([
               {
                    "message": "Reports created successfully"
               }
            ], status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MarketingReportDetailAPIView(APIView):
    def get_object(self, pk):
        try:
            return MarketingReport.objects.get(pk=pk)
        except MarketingReport.DoesNotExist:
            return None

    def get(self, request, pk):
        report = self.get_object(pk)
        if not report:
            return Response({'error': 'Marketing Report not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = MarketingReportDisplaySerializer(report)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        report = self.get_object(pk)
        if not report:
            return Response({'error': 'Marketing Report not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = MarketingReportUpdateSerializer(report, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Marketing Report updated successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        report = self.get_object(pk)
        if not report:
            return Response({
                "status": "0",
                "message": "Marketing Report not found",
                "errors": f"Marketing Report with id {pk} does not exist"
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            report.delete()
            return Response({
                "status": "1",
                "message": "Marketing Report deleted successfully"
            }, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({
                "status": "0",
                "message": "Marketing Report deletion failed",
                "errors": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
