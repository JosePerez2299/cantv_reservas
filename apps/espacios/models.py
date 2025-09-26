from django.db import models
from django.db.models import Q
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from apps.core.models import Ubicacion, PlataformaDigital
import os
import uuid


class Espacio(models.Model):

    class Tipo(models.TextChoices):
        FISICO = 'fisico', 'Físico'
        DIGITAL = 'digital', 'Digital'

    nombre = models.CharField(max_length=150, unique=True, blank=False,
                              validators=[
                                  RegexValidator(
                                      r"^[a-zA-Z][a-zA-Z0-9 ]*",
                                      message="El nombre del espacio debe comenzar con una letra, y solo puede contener letras, números y espacios."
                                  )
                              ])

    capacidad_maxima = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(5000), MinValueValidator(1)],
        help_text="Capacidad máxima (≤ 5000)"
    )

    tipo = models.CharField(
        max_length=20, choices=Tipo.choices)
  
    disponible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now=True)

    descripcion = models.TextField(
        "Descripción", null=True, blank=True
    )

    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Espacio"
        verbose_name_plural = "Espacios"
        ordering = ['tipo',  'nombre']
        indexes = [
            models.Index(fields=['tipo'])
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(capacidad_maxima__lte=5000),
                name='check_capacidad_max_5000'
            ),
        ]
    @property
    def ubicacion(self):
        if self.tipo == 'fisico':
            if self.detalle_fisico:
                return self.detalle_fisico.ubicacion.nombre
            return None

        elif self.tipo == 'digital':
            if self.detalle_digital:
                return self.detalle_digital.plataforma.nombre
        return None

    def __str__(self):
        return f"{self.nombre}"


class DetalleEspacioDigital(models.Model):
    espacio = models.OneToOneField(
        Espacio, on_delete=models.CASCADE, related_name='detalle_digital'
    )

    plataforma = models.ForeignKey(
        PlataformaDigital,
        help_text="Plataforma del espacio digital",
        on_delete=models.CASCADE,
        related_name='detalles'
    )

    url = models.URLField(
        max_length=200,
        help_text="URL del espacio digital",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Detalle Espacio Digital"
        verbose_name_plural = "Detalles de Espacios Digitales"
        constraints = [
            models.UniqueConstraint(
                fields=['espacio'],
                name='uniq_espacio_digital',
                violation_error_message="Ya existe un detalle de espacio digital para este espacio."
            )
        ]
    def clean(self):
        super().clean()
        # Si aún no se ha asignado FK, saltar validaciones dependientes de Espacio.
        if not self.espacio_id:
            return

        espacio = Espacio.objects.filter(pk=self.espacio_id).first()
        if not espacio:
            raise ValidationError({'espacio': 'Espacio inexistente.'})

        if espacio.tipo != Espacio.Tipo.DIGITAL:
            raise ValidationError({'espacio': 'El espacio debe ser de tipo digital.'})


    def __str__(self):
        return f"Espacio: {self.espacio.nombre} | Capacidad Máxima: {self.espacio.capacidad_maxima}"

def user_directory_path(instance, filename):
    ext = filename.split('.')[-1] 
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join("espacios/fisicos", filename)

class DetalleEspacioFisico(models.Model):
    class Tipo(models.TextChoices):
        SALON = 'salon', 'Salón'
        LABORATORIO = 'laboratorio', 'Laboratorio'
        AUDITORIO = 'auditorio', 'Auditorio'
        OTRO = 'otro', 'Otro'

    espacio = models.OneToOneField(
        Espacio, on_delete=models.CASCADE, related_name='detalle_fisico'
    )
    piso = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(40)],
        help_text="Piso en que se encuentra el espacio (≤ 40)"
    )
    tipo = models.CharField(
        max_length=20, choices=Tipo.choices)
    
    ubicacion = models.ForeignKey(
        Ubicacion, on_delete=models.CASCADE, related_name='espacios_fisicos')


    foto = models.ImageField(upload_to=user_directory_path, null=True, blank=True)

    class Meta:
        verbose_name = "Detalle Espacio Físico"
        verbose_name_plural = "Detalles de Espacios Físicos"
        constraints = [
            models.UniqueConstraint(
                fields=['espacio'],
                name='uniq_espacio_fisico',
                violation_error_message="Ya existe un detalle de espacio físico para este espacio."
            )
        ]

    def clean(self):
        super().clean()
        
        # # Validar que el espacio sea de tipo físico
        # if self.espacio and self.espacio.tipo != 'fisico':
        #     raise ValidationError({
        #         'espacio': f'El espacio "{self.espacio.nombre}" debe ser de tipo físico para tener detalles físicos.'
        #     })
        
        # # Validar que no existan detalles digitales para el mismo espacio
        # if self.espacio and hasattr(self.espacio, 'detalles_digitales') and self.espacio.detalles_digitales.exists():
        #     raise ValidationError({
        #         'espacio': f'El espacio "{self.espacio.nombre}" ya tiene detalles digitales. No puede tener ambos tipos de detalles.'
        #     })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Espacio: {self.espacio.nombre} | Capacidad Máxima: {self.espacio.capacidad_maxima}"


