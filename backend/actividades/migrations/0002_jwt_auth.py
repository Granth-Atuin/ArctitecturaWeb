# Generated migration for JWT Authentication & Participante integration

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('actividades', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='actividad',
            options={'ordering': ('fecha',), 'verbose_name': 'Actividad', 'verbose_name_plural': 'Actividades'},
        ),
        migrations.AlterField(
            model_name='actividad',
            name='capacidad',
            field=models.PositiveIntegerField(verbose_name='Capacidad'),
        ),
        migrations.CreateModel(
            name='Participante',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=150, verbose_name='Nombre completo')),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='participante',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Usuario',
                )),
            ],
            options={
                'verbose_name': 'Participante',
                'verbose_name_plural': 'Participantes',
            },
        ),
        migrations.CreateModel(
            name='RefreshToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_hash', models.CharField(max_length=64, unique=True, verbose_name='Hash del token')),
                ('expires_at', models.DateTimeField(verbose_name='Expira en')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creado en')),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='refresh_tokens',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Usuario',
                )),
            ],
            options={
                'verbose_name': 'Refresh Token',
                'verbose_name_plural': 'Refresh Tokens',
            },
        ),
        # Limpiar datos antiguos de inscripcion incompatibles con la nueva FK
        migrations.RunSQL(
            sql="DELETE FROM actividades_inscripcion;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterUniqueTogether(
            name='inscripcion',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='inscripcion',
            name='usuario',
        ),
        migrations.AddField(
            model_name='inscripcion',
            name='participante',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='inscripciones',
                to='actividades.participante',
                verbose_name='Participante',
            ),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='inscripcion',
            unique_together={('actividad', 'participante')},
        ),
    ]
