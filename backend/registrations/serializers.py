from rest_framework import serializers
from .models import Registration

VALID_KNOWLEDGE_AREAS = {'AI & ML', 'Software Dev', 'Data', 'Design & UX', 'Law', 'Project Mgmt', 'Other'}
VALID_DIETARY = {'None', 'Vegetarian', 'Vegan', 'Gluten-free', 'Halal', 'Nut allergy', 'Other'}


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = [
            'full_name', 'email', 'university', 'study_program', 'year_of_study',
            'knowledge_areas', 'team_preference', 'dietary_restrictions',
            'photo_consent', 'code_of_conduct', 'how_did_you_hear', 'cv',
            'discord_handle',
        ]

    def validate_knowledge_areas(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError('Select at least one knowledge area.')
        invalid = set(value) - VALID_KNOWLEDGE_AREAS
        if invalid:
            raise serializers.ValidationError(f'Invalid areas: {invalid}')
        return value

    def validate_dietary_restrictions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Must be a list.')
        invalid = set(value) - VALID_DIETARY
        if invalid:
            raise serializers.ValidationError(f'Invalid options: {invalid}')
        return value

    def validate_code_of_conduct(self, value):
        if not value:
            raise serializers.ValidationError('You must accept the Code of Conduct.')
        return value

    def validate_cv(self, value):
        if value and not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError('Only PDF files are accepted.')
        if value and value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('CV must be under 5 MB.')
        return value
