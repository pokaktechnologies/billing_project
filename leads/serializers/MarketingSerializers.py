from rest_framework import serializers
from ..models import *
from datetime import datetime
from django.utils import timezone
from accounts.models import SalesPerson

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'  # or specify the fields you want to include

    def create(self, validated_data):
        # Custom logic for creating a Location instance if needed
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Custom logic for updating a Location instance if needed
        return super().update(instance, validated_data)


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ['id', 'name']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'source']

class DisplaySourceSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)

    class Meta:
        model = Source
        fields = ['id', 'name', 'categories']

class CategoryReportSerializer(serializers.Serializer):
    category_id = serializers.IntegerField()
    calls = serializers.IntegerField()
    leads = serializers.IntegerField()

class LocationReportSerializer(serializers.Serializer):
    location_id = serializers.IntegerField()
    categories = CategoryReportSerializer(many=True)

class SourceReportSerializer(serializers.Serializer):
    source_id = serializers.IntegerField()
    locations = LocationReportSerializer(many=True)

class MarketingReportSerializer(serializers.Serializer):
    salesperson_id = serializers.IntegerField()
    sources = SourceReportSerializer(many=True)

    def validate(self, data):
        """
        Validate all IDs and relationships before creating any objects.
        """
        salesperson_id = data.get('salesperson_id')
        sources_data = data.get('sources', [])

        # Validate salesperson
        try:
            salesperson = SalesPerson.objects.get(id=salesperson_id)
        except SalesPerson.DoesNotExist:
            raise serializers.ValidationError({'salesperson_id': 'Invalid salesperson ID'})

        data['_salesperson'] = salesperson  # store for create

        # Validate all sources, locations, categories
        validated_items = []

        for source_item in sources_data:
            try:
                source = Source.objects.get(id=source_item['source_id'])
            except Source.DoesNotExist:
                raise serializers.ValidationError({'source_id': f"Source {source_item['source_id']} not found"})

            for location_item in source_item.get('locations', []):
                try:
                    location = Location.objects.get(id=location_item['location_id'])
                except Location.DoesNotExist:
                    raise serializers.ValidationError({'location_id': f"Location {location_item['location_id']} not found"})

                for category_item in location_item.get('categories', []):
                    try:
                        category = Category.objects.get(id=category_item['category_id'])
                    except Category.DoesNotExist:
                        raise serializers.ValidationError({'category_id': f"Category {category_item['category_id']} not found"})

                    # Check category belongs to source
                    if category.source.id != source.id:
                        raise serializers.ValidationError({
                            'category_id': f"Category {category.name} (ID: {category.id}) does not belong to Source {source.name} (ID: {source.id})"
                        })

                    # Store validated record
                    validated_items.append({
                        'source': source,
                        'location': location,
                        'category': category,
                        'calls': category_item['calls'],
                        'leads': category_item['leads']
                    })

        data['_validated_items'] = validated_items
        return data

    def create(self, validated_data):
        """
        Create all MarketingReport objects after validation.
        """
        request = self.context.get('request')
        salesperson = validated_data['_salesperson']
        validated_items = validated_data['_validated_items']

        reports = []
        for item in validated_items:
            report = MarketingReport.objects.create(
                salesperson=salesperson,
                user=request.user if request else None,
                date=request.data.get('date', timezone.now().date()),
                source=item['source'],
                location=item['location'],
                category=item['category'],
                calls=item['calls'],
                leads=item['leads']
            )
            reports.append(report)

        return reports


class MarketingReportUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingReport
        fields = "__all__"

    def validate(self, data):
        """
        Ensure that the source, location, and category are correctly related.
        """
        source = data.get('source', getattr(self.instance, 'source'))
        # location = data.get('location', getattr(self.instance, 'location'))
        category = data.get('category', getattr(self.instance, 'category'))

        # Check if the category belongs to the source
        if category.source != source:
            raise serializers.ValidationError({
                'category': f"Category '{category}' does not belong to Source '{source}'."
            })
        
        return data
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


    
class MarketingReportDisplaySerializer(serializers.ModelSerializer):
    salesperson = serializers.CharField(source='salesperson.first_name')
    salesperson_id = serializers.IntegerField(source='salesperson.id')
    source = serializers.CharField(source='source.name')
    source_id = serializers.IntegerField(source='source.id')
    location = serializers.CharField(source='location.name')
    location_id = serializers.IntegerField(source='location.id')
    category = serializers.CharField(source='category.name')
    category_id = serializers.IntegerField(source='category.id')

    class Meta:
        model = MarketingReport
        fields = [
            'id', 'date',
            'salesperson_id', 'salesperson',
            'source_id', 'source',
            'location_id', 'location',
            'category_id', 'category',
            'calls', 'leads',
        ]
