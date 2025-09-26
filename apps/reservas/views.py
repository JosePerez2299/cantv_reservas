"""
Views para las reservas

* ReservaListView: Muestra una lista de reservas con un formulario de filtrado
* ReservaCreateView: Crea una nueva reserva
* ReservaUpdateView: Edita una reserva existente
* ReservaDetailView: Muestra los detalles de una reserva
* ReservaDeleteView: Elimina una reserva existente

"""
import json
from django.shortcuts import render
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView
from formtools.wizard.views import SessionWizardView

from apps.espacios.forms import EmptyForm
from .models import Reserva, ReservaEspacio, DetalleReservaDigital, DetalleReservaFisico
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django_filters.views import FilterView
from library.mixins.helpers import *
from django.db.models.functions import Lower
from django.urls import reverse_lazy, reverse
from .filters import *
from .forms import *
from django.db.models import Q, Count
from django.http import JsonResponse
from datetime import datetime
from django.views import View
from django.utils import timezone
from django.views.generic import TemplateView
from .services import *
from django.shortcuts import get_object_or_404
def qs_condiciones(user):
    if user.is_admin:
        return Q()

    else:
        return Q(p00_solicitante=user.p00)

class ReservasMonthlyCount(LoginRequiredMixin, PermissionRequiredMixin,View):
    """
    Devuelve un conteo de reservas por día para un rango de fechas,
    opcionalmente filtrado por estado.
    Usado por el calendario para mostrar indicadores de actividad.
    """
    permission_required = 'reservas.view_reserva'
    
    def get(self, request):
        start_str = request.GET.get('start')
        end_str = request.GET.get('end')
        status = request.GET.get('status')

        try:
            if start_str and end_str:
                start_date = datetime.fromisoformat(start_str.split('T')[0])
                end_date = datetime.fromisoformat(end_str.split('T')[0])
            else:
                return JsonResponse({'error': 'Faltan fechas'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Formato de fecha invalido'}, status=400)

        reservas_por_usuario = lista_reservas_usuario(self.request.user)
        queryset = reservas_por_usuario.filter(
            fecha_uso__gte=start_date,
            fecha_uso__lte=end_date,
        )


        possible_states = ['pendiente', 'aprobada', 'rechazada']

        if status and status in possible_states:
            queryset = queryset.filter(estado=status)
        else: 
            queryset = queryset.filter(estado__in=possible_states)

        daily_counts = queryset.values('fecha_uso').annotate(
            pendiente_count=Count('id', filter=Q(estado='pendiente')),
            aprobada_count=Count('id', filter=Q(estado='aprobada')),
            rechazada_count=Count('id', filter=Q(estado='rechazada'))
        ).order_by('fecha_uso')
        return JsonResponse(list(daily_counts), safe=False)


class CalendarioReservasView(LoginRequiredMixin, TemplateView):
    """
    Muestra el calendario de reservas
    """
    template_name = 'reservas/calendario.html'


class ReservasByDate(PermissionRequiredMixin, FilterView):
    """
    Muestra una lista de reservas filtradas por fecha
    """
    model = Reserva
    permission_required = 'reservas.view_reserva'
    template_name = 'reservas/calendario_reservas_cardslist.html'
    paginate_by = 7
    filterset_class = ReservaFilterCards
    context_object_name = 'reservas'   
    ordering = ['hora_inicio']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Agregar parámetros actuales al contexto para la paginación
        context['current_filters'] = self.request.GET.dict()
        
        # Si es una petición HTMX, podemos agregar información adicional
        if self.request.headers.get('HX-Request'):
            context['is_htmx'] = True
            
        return context

    def get_queryset(self):
        return lista_reservas_usuario(self.request.user)

    
class ReservaListView(LoginRequiredMixin, ListCrudMixin, PermissionRequiredMixin, FilterView):
    """
    Muestra una lista de reservas con un formulario de filtrado
    """
    model = Reserva
    permission_required = 'reservas.view_reserva'
    template_name = 'reservas/reservas_table.html'
    paginate_by = 10
    can_export = True

    # Columnas que mostramos en la tabla HTML
    cols = {
        'id': {'label': 'ID', 'sortable': True},
        'p00_solicitante': {'label': 'P00 solicitante', 'sortable': True},
        'modalidad': {'label': 'Modalidad', 'sortable': True},
        'espacios': {'label': 'Espacios', 'sortable': False},
        'fecha_uso': {'label': 'Fecha de uso', 'sortable': True},
        'estado': {'label': 'Estado', 'sortable': True},
        'aprobado_por': {'label': 'Aprobado por', 'sortable': True},
    }

    # Es importante el nombre (key) que sean los definidos, para que el template pueda usarlos. 
    # El value debe ser el nombre de la url que se define en urls.py
    crud_urls = {
        'create': 'reserva_create',
        'view': 'reserva_view',
        'edit': 'reserva_edit',
        'delete': 'reserva_delete',
    }
    

    # Filtros
    filterset_class = ReservaFilter 


    def get_queryset(self):
        return lista_reservas_usuario(self.request.user)
    

class ReservaCreateWizardView(LoginRequiredMixin, PermissionRequiredMixin,SessionWizardView):
    """
    Crea una nueva reserva
    """
    permission_required = 'reservas.add_reserva'
    form_list = [
        ('contacto', ContactoForm),
        ('reserva', ReservaForm),
        ('requerimiento', RequerimientoForm),
        ('espacio_presencial', ReservaEspacioFisicoForm),
        ('espacio_digital', ReservaEspacioDigitalForm),
        ('detalle_digital', DetalleReservaDigitalForm),
        ('resumen', EmptyForm)
    ]
    
    def process_step(self, form):
        """
        Procesa cada paso del wizard y guarda mensajes de error si ocurren
        """
        try:
            return super().process_step(form)
        except ValidationError as e:
            # Guardar el error para usarlo después
            self.storage.extra_data['validation_error'] = str(e)
            return self.get_form_step_data(form)
    
    def render_next_step(self, form, **kwargs):
        """
        Personaliza el comportamiento cuando se avanza al siguiente paso
        """
        # Verifica si hay un error de validación almacenado
        if self.storage.extra_data.get('validation_error'):
            error_msg = self.storage.extra_data.pop('validation_error')
            # Redirigir al paso 1 (reserva) cuando hay un error de solapamiento
            self.storage.current_step = 'reserva'
            form = self.get_form(
                step='reserva',
                data=self.storage.get_step_data('reserva'),
                files=self.storage.get_step_files('reserva')
            )
            form.add_error(None, error_msg)  # Agregar error al formulario
            return self.render(form, **kwargs)
        
        # Comportamiento normal si no hay errores
        return super().render_next_step(form, **kwargs)
    
    def get_form_kwargs(self, step=None):
        """
        Pasamos el objeto reserva temporal a los formularios de espacio
        para que puedan validar el solapamiento
        """
        kwargs = super().get_form_kwargs(step)
        
        # Solo para los pasos que necesitan la reserva para validar solapamientos
        if step in ['espacio_presencial', 'espacio_digital']:
            # Obtenemos los datos de contacto y reserva para crear una reserva temporal
            contacto_data = self.get_cleaned_data_for_step('contacto') or {}
            reserva_data = self.get_cleaned_data_for_step('reserva') or {}
            
            if contacto_data and reserva_data:
                # Creamos un objeto reserva temporal (sin guardar en la BD)
                from apps.reservas.models import Reserva
                reserva = Reserva(
                    p00_solicitante=contacto_data.get('p00_solicitante', ''),
                    nombre_solicitante=contacto_data.get('nombre_solicitante', ''),
                    fecha_uso=reserva_data.get('fecha_uso'),
                    hora_inicio=reserva_data.get('hora_inicio'),
                    hora_fin=reserva_data.get('hora_fin')
                )
                kwargs['reserva'] = reserva
                
        return kwargs

    condition_dict = {
        'requerimiento': es_presencial_o_mixta,
        'espacio_presencial': es_presencial_o_mixta,
        'espacio_digital': es_virtual_o_mixta,
        'detalle_digital': es_virtual_o_mixta,
    }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Reserva de Espacios'
        ctx['subtitle'] = 'Complete la información requerida'
        ctx['header_icon'] = 'calendar-alt'
        ctx['url'] = reverse_lazy('reserva_create')
        
        # Steps info
        all_steps = list(self.get_form_list().keys())
        current_index = all_steps.index(self.steps.current)
        
        ctx['all_steps'] = all_steps
        ctx['current_index'] = current_index
        
        if self.steps.current == 'resumen':

            ctx['resumen_data'] = self.get_resumen_data()
            
        return ctx
    
    def get_resumen_data(self):
        """Recopila todos los datos del wizard para mostrar en el resumen"""
        reserva_data = {}   
        # Obtener la lista de pasos que realmente se han mostrado/usado
        all_steps = self.get_form_list().keys()
        for step in all_steps:
            try:
                data = self.get_cleaned_data_for_step(step) or {}
                reserva_data[step] = data
            except KeyError:
                # Si el paso fue omitido por una condición, simplemente lo saltamos
                continue
        return reserva_data
    
    def get_template_names(self):
        # Templates para el wizard de creación de reservas
        TEMPLATES = {
            'contacto': 'reservas/contacto_form.html',
            'reserva': 'reservas/reserva_form.html',
            'tipo': 'reservas/tipo_form.html',
            'detalle': 'reservas/detalles_digitales_form.html',
            'requerimiento': 'reservas/requerimiento_form.html',
            'espacio_presencial': 'reservas/espacio_fisico_form.html',
            'espacio_digital': 'reservas/espacio_digital_form.html',
            'detalle_digital': 'reservas/detalles_digitales_form.html',
            'resumen': 'reservas/resumen_form.html'
        }
        return [TEMPLATES[self.steps.current]]
    
    def done(self, form_list, form_dict, **kwargs):
        try:
            # Todas las operaciones se realizan dentro de una transacción atómica
            with transaction.atomic():
                # Obtenemos los datos de cada paso del wizard
                contacto_data = form_dict['contacto'].cleaned_data
                reserva_data = form_dict['reserva'].cleaned_data
                modalidad = reserva_data.get('modalidad')
                
                # Creamos la reserva base
                reserva = Reserva(
                    p00_solicitante=contacto_data.get('p00_solicitante'),
                    nombre_solicitante=contacto_data.get('nombre_solicitante'),
                    email_solicitante=contacto_data.get('email_solicitante'),
                    telefono_solicitante=contacto_data.get('telefono_solicitante'),
                    vicepresidencia_solicitante=contacto_data.get('vicepresidencia_solicitante'),
                    gerencia_solicitante=contacto_data.get('gerencia_solicitante'),
                    modalidad=modalidad,
                    tipo_solicitud=reserva_data.get('tipo_solicitud'),
                    tipo_actividad=reserva_data.get('tipo_actividad'),
                    fecha_uso=reserva_data.get('fecha_uso'),
                    hora_inicio=reserva_data.get('hora_inicio'),
                    hora_fin=reserva_data.get('hora_fin'),
                    motivo=reserva_data.get('motivo'),
                )
                
                # Si tiene requerimientos (presencial o mixta)
                if es_presencial_o_mixta(self):
                    requerimiento_data = form_dict['requerimiento'].cleaned_data
                    reserva.requerimientos = requerimiento_data.get('requerimientos')
                    reserva.observacion = requerimiento_data.get('observacion')
                
                # Guardamos la reserva primero para poder crear las relaciones
                reserva.save()
                
                # Procesamos espacio presencial si aplica
                if es_presencial_o_mixta(self):
                    espacio_presencial_data = form_dict['espacio_presencial'].cleaned_data
                    espacio_presencial = espacio_presencial_data.get('espacio')
                    
                    if espacio_presencial:
                        # Creamos la relación reserva-espacio físico
                        reserva_espacio_fisico = ReservaEspacio(
                            reserva=reserva,
                            espacio=espacio_presencial,
                            numero_participantes=espacio_presencial_data.get('numero_participantes')
                        )
                        # La validación de solapamiento ocurrirá en el método clean() que ya implementamos
                        reserva_espacio_fisico.clean()
                        reserva_espacio_fisico.save()
                        
                        # Creamos el detalle físico relacionado
                        detalle_fisico = DetalleReservaFisico(
                            reserva_espacio=reserva_espacio_fisico,
                            numero_participantes_confirmados=0  # Inicialmente 0 confirmados
                        )
                        detalle_fisico.save()
                
                # Procesamos espacio digital si aplica
                if es_virtual_o_mixta(self):
                    espacio_digital_data = form_dict['espacio_digital'].cleaned_data
                    espacio_digital = espacio_digital_data.get('espacio')
                    
                    if espacio_digital:
                        # Creamos la relación reserva-espacio digital
                        reserva_espacio_digital = ReservaEspacio(
                            reserva=reserva,
                            espacio=espacio_digital,
                            numero_participantes=espacio_digital_data.get('numero_participantes')
                        )
                        # La validación de solapamiento ocurrirá en el método clean() que ya implementamos
                        reserva_espacio_digital.clean()
                        reserva_espacio_digital.save()
                        
                        # Procesamos los detalles digitales
                        detalle_digital_data = form_dict['detalle_digital'].cleaned_data
                        detalle_digital = DetalleReservaDigital(
                            reserva_espacio=reserva_espacio_digital,
                            anfitrion_usuario=detalle_digital_data.get('anfitrion_usuario'),
                            ubicacion_transmision=detalle_digital_data.get('ubicacion_transmision'),
                            espacio_transmision=detalle_digital_data.get('espacio_transmision')
                        )
                        detalle_digital.save()
            
            response = HttpResponse(status=204)
            response['HX-Trigger'] = json.dumps({'showMessage': 'Se ha creado exitosamente'})
            return response
            
        except ValidationError as e:
            # Capturamos errores de validación (como el solapamiento de reservas)
            print(f"Error de validación: {e}")
            
            # Redirigimos al paso de reserva con el error
            self.storage.extra_data['validation_error'] = str(e)
            self.storage.current_step = 'reserva'  # Regresamos al paso de reserva
            
            # Preparamos el formulario con el error
            form = self.get_form(
                step='reserva',
                data=self.storage.get_step_data('reserva'),
                files=self.storage.get_step_files('reserva')
            )
            form.add_error(None, str(e))
            
            # Renderizamos el paso de reserva con el error
            return self.render(form)
        
        except Exception as e:
            # Capturamos cualquier otro tipo de error que pueda ocurrir
            print(f"Error inesperado: {e}")
            # Redirigimos al paso inicial con un mensaje de error
            self.storage.extra_data['validation_error'] = f"Ocurrió un error inesperado: {e}"
            self.storage.current_step = 'contacto'
            
            form = self.get_form(
                step='contacto',
                data=self.storage.get_step_data('contacto'),
                files=self.storage.get_step_files('contacto')
            )
            form.add_error(None, f"Ocurrió un error inesperado: {e}")
            
            return self.render(form)


class ReservaUpdateWizardView(LoginRequiredMixin, PermissionRequiredMixin, SessionWizardView):
    permission_required = 'reservas.change_reserva'

    form_list = [
        ('reserva', ReservaUpdateForm),
        ('detalle_digital', DetalleReservaDigitalForm),
        ('requerimiento', RequerimientoForm),

    ]

    condition_dict = {
        'requerimiento': es_presencial_o_mixta,
        'detalle_digital': es_virtual_o_mixta,
    }

    def dispatch(self, request, *args, **kwargs):
        # Carga la instancia que vamos a editar (pk en la URL)
        self.reserva = get_object_or_404(Reserva, pk=kwargs.get('pk'))

        if self.reserva.estado != 'pendiente':
            raise Http404
        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Reserva de Espacios'
        ctx['subtitle'] = 'Complete la información requerida'
        ctx['header_icon'] = 'calendar-alt'
        ctx['url'] = reverse_lazy('reserva_edit', args=[self.reserva.pk])
        
        # Steps info
        all_steps = list(self.get_form_list().keys())
        current_index = all_steps.index(self.steps.current)
        
        ctx['all_steps'] = all_steps
        ctx['current_index'] = current_index

        return ctx

    def get_form_instance(self, step):
        return self.reserva
      
    
    def get_template_names(self):
        TEMPLATES = {
            "reserva": "reservas/reservas_edit.html",
            'detalle_digital': 'reservas/detalles_digitales_form.html',
            "requerimiento": "reservas/requerimiento_form.html",
        }
        return [TEMPLATES[self.steps.current]]
    
    def done(self, form_list, **kwargs):
        
        try:
            with transaction.atomic():
                reserva = form_list[0].save(commit=False)

                if reserva.modalidad == 'Presencial':
                    form1 = form_list[1].save(commit=False)
                    reserva.requerimiento = form1.requerimientos
                    reserva.observacion = form1.observacion
                reserva.save()
                response = HttpResponse(status=204)
                response['HX-Trigger'] = json.dumps({'showMessage': 'Se ha creado exitosamente'})
                return response
        except Exception as e:
            # En caso de error, la transacción se revierte automáticamente
            return HttpResponse(f'Error al guardar: {str(e)}', status=500)

    
class ReservaDetailView(LoginRequiredMixin, PermissionRequiredMixin,  FormContextMixin, DetailView):
    """
    Muestra los detalles de una reserva
    """
    model = Reserva
    object_context_name = 'reserva'
    template_name = 'reservas/reservas_detail.html'
    permission_required = 'reservas.view_reserva'
    html_title = 'Detalles de Reserva'
    url = reverse_lazy('reserva_view')

    def dispatch(self, request, *args, **kwargs):
        # Solo permitir peticiones AJAX/HTMX
        if not (request.headers.get('HX-Request') or request.headers.get('X-Requested-With') == 'XMLHttpRequest'):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return lista_reservas_usuario(self.request.user)
    
class ReservaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, AjaxDeleteMixin, DeleteView):
    """
    Elimina una reserva existente
    """
    model = Reserva
    template_name = 'reservas/delete.html'
    success_url = reverse_lazy('reserva') 
    permission_required = 'reservas.delete_reserva'
    url = 'reserva_delete'

    details = [ 
        {'label': 'Fecha de uso', 'value': 'fecha_uso'},
        {'label': 'Usuario', 'value': 'usuario'},
        {'label': 'Estado', 'value': 'estado'},
        {'label': 'Aprobado por', 'value': 'aprobado_por'},
        {'label': 'Espacio', 'value': 'espacio'},
        {'label': 'Motivo', 'value': 'motivo'},
        {'label': 'Hora inicio', 'value': 'hora_inicio'},
        {'label': 'Hora fin', 'value': 'hora_fin'},
    ]

    def get_queryset(self):
        reservas_por_usuario = lista_reservas_usuario(self.request.user)
        qs = reservas_por_usuario.filter(Q(estado='pendiente'))
        return qs

class ReservaApproveView(LoginRequiredMixin, PermissionRequiredMixin, AjaxFormMixin, UpdateView):
    """
    Aprobar una reserva existente
    """
    model = Reserva
    form_class = ReservaApproveForm  
    template_name = 'reservas/reservas_approve.html'
    success_url = reverse_lazy('reserva')
    permission_required = 'reservas.change_reserva'

    def success_message(self):
        return 'Reserva editada correctamente'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['url'] = reverse_lazy('reserva_approve', args=[self.object.pk])
        ctx['title'] = 'Gestionar Reserva'
        ctx['subtitle'] = 'Aprobar/Rechazar la reserva'
        return ctx

    def get_queryset(self):
        if not self.request.user.is_admin:
            raise Http404
        qs = super().get_queryset()
        qs = qs.filter(Q(estado='pendiente'))
        return qs

    def form_valid(self, form):
        # Registrar el usuario que aprobo la reserva
        form.instance.aprobado_por = self.request.user
        # Registrar la fecha y hora del cambio de estado en el servidor
        form.instance.fecha_cambio_estado = timezone.now()
        return super().form_valid(form)