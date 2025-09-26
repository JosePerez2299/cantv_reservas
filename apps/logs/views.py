from auditlog.models import LogEntry
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView
from django.conf import settings
from django.db.models import Case, When, Value, CharField
from django.contrib.contenttypes.models import ContentType
from apps.reservas.models import *
from library.utils.utils import get_logs
from .filters import LogFilter
from library.mixins.helpers import ListCrudMixin, SmartOrderingMixin
from django_filters.views import FilterView

class LogListView(LoginRequiredMixin, PermissionRequiredMixin, ListCrudMixin, FilterView ):
    """
    Muestra una lista de logs con un formulario de filtrado
    """
    model = LogEntry    
    permission_required = 'auditlog.view_logentry' 
    template_name = 'logs/log_table.html'
    paginate_by = 10
    filterset_class = LogFilter
    cols = {
        'id': {'label': 'Log ID'},
        'actor': {'label': 'Usuario'},
        'object_repr':  {'label': 'Recurso'},
        'tipo': {'label': 'Modulo'},
        'action_label': {'label': 'Acción'},
        'timestamp': {'label': 'Fecha'},
    }

    can_export = False
    crud_urls = {
        'view': 'log_detail',
    }
    actions = True

    def get_queryset(self):

        user = self.request.user
        qs = get_logs(user)

        if qs is None:
            return []
        
        action = {
            LogEntry.Action.CREATE: 'Crear',
            LogEntry.Action.UPDATE: 'Actualizar',
            LogEntry.Action.DELETE: 'Eliminar',
        }
        qs = qs.annotate(
            action_label=Case(
                When(action=LogEntry.Action.CREATE, then=Value(action[LogEntry.Action.CREATE])),
                When(action=LogEntry.Action.UPDATE, then=Value(action[LogEntry.Action.UPDATE])),
                When(action=LogEntry.Action.DELETE, then=Value(action[LogEntry.Action.DELETE])),
                default=Value('-'),
                output_field=CharField()
            ),
            tipo=Case(
                When(content_type=ContentType.objects.get_for_model(Usuario), then=Value('Usuario')),
                When(content_type=ContentType.objects.get_for_model(Espacio), then=Value('Espacio')),
                When(content_type=ContentType.objects.get_for_model(Reserva), then=Value('Reserva')),
                default=Value('-'),
                output_field=CharField()
            ),
            object=Case(
                When(content_type=ContentType.objects.get_for_model(Usuario), then=Value('Usuario')),
                When(content_type=ContentType.objects.get_for_model(Espacio), then=Value('Espacio')),
                When(content_type=ContentType.objects.get_for_model(Reserva), then=Value('Reserva')),
                default=Value('-'),
                output_field=CharField()
            )
        )

        return qs


class LogDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Muestra los detalles de un log
    """
    model = LogEntry
    permission_required = 'auditlog.view_logentry'
    template_name = 'logs/log_detail.html'
    
   