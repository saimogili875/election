from django.db import migrations
import json
from pathlib import Path

def seed_areas_and_prompts(apps, schema_editor):
    Area = apps.get_model('wardapp', 'Area')
    PromptVersion = apps.get_model('wardapp', 'PromptVersion')

    from wardapp.constants import AREAS
    for name in AREAS:
        Area.objects.get_or_create(name=name)

    # Seed prompt from fixture
    fixture_path = Path(__file__).resolve().parent.parent / 'fixtures' / 'initial_prompt.json'
    if fixture_path.exists():
        with open(fixture_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                fields = item['fields']
                PromptVersion.objects.get_or_create(
                    id=item['pk'],
                    defaults={
                        'name': fields['name'],
                        'text': fields['text'],
                        'created_at': fields['created_at'],
                    }
                )

def reverse_seed(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('wardapp', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_areas_and_prompts, reverse_seed),
    ]
