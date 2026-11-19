# Zoom de carte décimal : la mini-carte des Paramètres écrit un zoom
# à une décimale, MapLibre le gère nativement.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_reglages'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reglages',
            name='zoom_carte',
            field=models.FloatField(default=16, verbose_name='zoom de la carte'),
        ),
    ]
