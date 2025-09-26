from apps.reservas.models import *
from datetime import datetime
from math import ceil, floor
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType

def get_user_groups(user):
    """
    Devuelve una lista de nombres de los grupos a los que pertenece un usuario.

    Argumentos:
        user (User): Una instancia de usuario de Django.

    Retorna:
        list: Una lista de cadenas que representan los nombres de los grupos del usuario.
    """
    return [group.name for group in user.groups.all()]


def get_all_cols(model):
    """
    Devuelve una lista de nombres de los campos de un modelo.

    Argumentos:
        model (Model): Un modelo de Django.

    Retorna:
        list: Una lista de cadenas que representan los nombres de los campos del modelo.
    """
    return [field.name for field in model._meta.get_fields()]


from datetime import datetime
from math import ceil, floor
from django.db.models import Q, Count

def get_stats(request):
    """Punto de entrada principal para obtener estadísticas según el tipo de usuario"""
    try:
        # Obtener últimos 5 logs
        logs = get_logs(request.user)[:5]
    except:
        logs = []
    
    user = request.user
    stats_func_map = {
        'is_admin': get_stats_administrador,
        'is_usuario': get_stats_administrador, 
    }
    
    for attr, func in stats_func_map.items():
        if getattr(user, attr, False):
            stats = func(request)
            stats['logs'] = logs
            return stats
            
    return {'cards': [], 'month_summary': [], 'logs': []}


class StatsCalculator:
    """Clase para centralizar los cálculos de estadísticas"""
    
    def __init__(self, request):
        self.request = request
        self.user = request.user
        self.month = datetime.now().month
        self.year = datetime.now().year
        self.now = datetime.now()
    
    def get_reserva_counts(self, base_filter=None):
        """Obtiene conteos de reservas por estado"""
        if base_filter is None:
            base_filter = Q()
            
        return {
            'pendientes': Reserva.objects.filter(base_filter, estado=Reserva.Estado.PENDIENTE).count(),
            'aprobadas': Reserva.objects.filter(base_filter, estado=Reserva.Estado.APROBADA).count(),
            'rechazadas': Reserva.objects.filter(base_filter, estado=Reserva.Estado.RECHAZADA).count()
        }
    
    def get_reserva_counts_mes(self, base_filter=None):
        """Obtiene conteos de reservas del mes actual por estado"""
        month_filter = Q(fecha_uso__month=self.month, fecha_uso__year=self.year)
        if base_filter is None:
            base_filter = Q()
        
        combined_filter = base_filter & month_filter
        
        return {
            'total': Reserva.objects.filter(combined_filter).count(),
            'aprobadas': Reserva.objects.filter(combined_filter, estado=Reserva.Estado.APROBADA).count(),
            'pendientes': Reserva.objects.filter(combined_filter, estado=Reserva.Estado.PENDIENTE).count(),
            'rechazadas': Reserva.objects.filter(combined_filter, estado=Reserva.Estado.RECHAZADA).count()
        }
    
    def calculate_percentages(self, counts_mes):
        """Calcula porcentajes basados en conteos mensuales"""
        total = counts_mes['total']
        if total == 0:
            return {'aprobadas': 0, 'pendientes': 0, 'rechazadas': 0}
        
        return {
            'aprobadas': (counts_mes['aprobadas'] / total) * 100,
            'pendientes': (counts_mes['pendientes'] / total) * 100,
            'rechazadas': (counts_mes['rechazadas'] / total) * 100
        }
    
    def get_proximas_reservas(self, base_filter=None):
        """Obtiene las próximas reservas"""
        if base_filter is None:
            base_filter = Q()
            
        return Reserva.objects.filter(
            base_filter,
            estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.APROBADA],
            fecha_uso__gte=self.now
        ).order_by('fecha_uso', 'hora_inicio')[:5]
    
    def create_month_summary(self, counts_mes, percentages, use_ceil_floor=True):
        """Crea el resumen mensual estandarizado"""
        round_func = {'aprobadas': ceil, 'pendientes': ceil, 'rechazadas': floor} if use_ceil_floor else {'aprobadas': floor, 'pendientes': floor, 'rechazadas': floor}
        
        return {
            'total': counts_mes['total'],
            'items': [
                {
                    'title': 'Reservas Aprobadas',
                    'value': round_func['aprobadas'](percentages['aprobadas']),
                    'count': counts_mes['aprobadas'],
                    'color': 'success'
                },
                {
                    'title': 'Reservas Pendientes',
                    'value': round_func['pendientes'](percentages['pendientes']),
                    'count': counts_mes['pendientes'],
                    'color': 'warning'
                },
                {
                    'title': 'Reservas Rechazadas',
                    'value': round_func['rechazadas'](percentages['rechazadas']),
                    'count': counts_mes['rechazadas'],
                    'color': 'error'
                }
            ]
        }
    
    def create_base_response(self, cards, month_summary, proximas_reservas):
        """Crea la estructura base de respuesta"""
        return {
            'cards': cards,
            'today': self.now,
            'month_summary': month_summary,
            'next_reservations': proximas_reservas,
        }


def get_stats_administrador(request):
    """Estadísticas para administradores"""
    calc = StatsCalculator(request)
    
    # Conteos generales
    counts = calc.get_reserva_counts()
    counts_mes = calc.get_reserva_counts_mes()
    percentages = calc.calculate_percentages(counts_mes)
    
    # Estadísticas adicionales específicas del admin
    espacios_disponibles = Espacio.objects.filter(disponible=True).count()
    espacios_no_disponibles = Espacio.objects.filter(disponible=False).count()
    usuarios = Usuario.objects.count()
    
    # Próximas reservas
    proximas_reservas = calc.get_proximas_reservas()
    
    # Cards específicas del admin
    cards = [
        {'title': 'Reservas Aprobadas', 'value': counts['aprobadas'], 'icon': 'reserva', 'color': 'text-success'},
        {'title': 'Reservas Pendientes', 'value': counts['pendientes'], 'icon': 'reserva', 'color': 'text-warning'},
        {'title': 'Reservas Rechazadas', 'value': counts['rechazadas'], 'icon': 'reserva', 'color': 'text-error'},
        {'title': 'Espacios Disponibles', 'value': espacios_disponibles, 'icon': 'espacio', 'color': 'text-success'},
        {'title': 'Espacios No Disponibles', 'value': espacios_no_disponibles, 'icon': 'espacio', 'color': 'text-error'},
        {'title': 'Usuarios Registrados', 'value': usuarios, 'icon': 'usuario', 'color': 'text-info'},
    ]
    
    month_summary = calc.create_month_summary(counts_mes, percentages, use_ceil_floor=True)
    
    return calc.create_base_response(cards, month_summary, proximas_reservas)


def get_stats_usuario(request):
    """Estadísticas para usuarios regulares"""
    calc = StatsCalculator(request)
    
    # Filtro base para el usuario actual
    user_filter = Q(usuario=request.user)
    
    # Conteos del usuario
    counts = calc.get_reserva_counts(user_filter)
    counts_mes = calc.get_reserva_counts_mes(user_filter)
    percentages = calc.calculate_percentages(counts_mes)
    
    # Próximas reservas del usuario
    proximas_reservas = calc.get_proximas_reservas(user_filter)
    
    # Cards específicas del usuario
    cards = [
        {'title': 'Mis Reservas Aprobadas', 'value': counts['aprobadas'], 'icon': 'reserva', 'color': 'text-success'},
        {'title': 'Mis Reservas Pendientes', 'value': counts['pendientes'], 'icon': 'reserva', 'color': 'text-warning'},
        {'title': 'Mis Reservas Rechazadas', 'value': counts['rechazadas'], 'icon': 'reserva', 'color': 'text-error'},
    ]
    
    month_summary = calc.create_month_summary(counts_mes, percentages, use_ceil_floor=False)
    
    return calc.create_base_response(cards, month_summary, proximas_reservas)


def get_logs(user):

    # TO DO: Actualizar query. Ya el grupo moderador no existe
    qs = LogEntry.objects.all()
    ct_reserva = ContentType.objects.get_for_model(Reserva)

    # Todos los logs de usuarios y moderadores, incluyendo a sí mismo
    if user.is_admin:
        filtro_usuario = Q(actor__groups__name__in=[ user.GRUPOS.MODERADOR, user.GRUPOS.USUARIO]) | Q(actor=user)
        return qs.filter(filtro_usuario)
    
    # Todos los logs de reservas de mi ubicación y piso, o donde el actor es el usuario
    if user.is_moderador:
        filtro_usuario = Q(actor=user)

        mis_reservas = Reserva.objects.filter(
            Q(Q(espacio__ubicacion=user.ubicacion) & Q(espacio__piso=user.piso)) |
            Q(usuario=user) |
            Q(aprobado_por=user)
        ).values_list('pk', flat=True)

        filtro_reserva_mi_ubicacion = Q(
            Q(content_type=ct_reserva) &
            Q(object_id__in=mis_reservas)
        )
        # Retornar todos los log donde actor es moderador o usuario
        qs = qs.filter(filtro_usuario | filtro_reserva_mi_ubicacion)
        return qs
    
    # Todos los logs de reservas de mi ubicación y piso, o donde el actor es el usuario
    if user.is_usuario:
        filtro_usuario = Q(actor=user)
        mis_reservas = Reserva.objects.filter(
            Q(usuario=user)
        ).values_list('pk', flat=True)
        
        filtro_reserva_mi_ubicacion = Q(
            Q(content_type=ct_reserva) &
            Q(object_id__in=mis_reservas)
        )
        # Retornar todos los log donde actor es usuario
        qs = qs.filter(filtro_usuario | filtro_reserva_mi_ubicacion)
        return qs
        