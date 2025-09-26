from django import template
from django.utils.safestring import mark_safe
from apps.reservas.models import *
from apps.core.templatetags.model_extras import get_attr
from datetime import datetime
from datetime import date
from django.urls import reverse
from django.conf import settings
from django.utils.html import format_html
register = template.Library()

@register.simple_tag
def get_icon(icon_name):

    dict_icons = {
        'reportes': 'fas fa-chart-line',
        'listado': 'fas fa-list-alt',
        'calendario': 'fas fa-calendar-alt',
        'reserva': 'fas fa-calendar-alt',
        'reservas': 'fas fa-calendar-alt',
        'espacio': 'fas fa-building',
        'espacios': 'fas fa-building',
        'usuario': 'fas fa-users',
        'usuarios': 'fas fa-users',
        'actividad': 'fas fa-clipboard-list',
        'dashboard': 'fas fa-home',
        'inicio': 'fas fa-home',

        'view': 'fas fa-eye',
        'edit': 'fas fa-edit',
        'delete': 'fas fa-trash',
        'add': 'fas fa-plus',
        'search': 'fas fa-search',
        'filter': 'fas fa-filter',
        'sort': 'fas fa-sort',
    }

    icon_class = dict_icons.get(icon_name)
    if icon_class is None:
        icon_class = 'fas fa-info-circle'

    return mark_safe(f'<i class="{icon_class}"></i>')

@register.simple_tag(takes_context=True)
def get_td_html(context, obj, field):
    """
    Devuelve un fragmento HTML (<td> o contenido para <td>) según el campo y la instancia.
    Usa format_html para escapar valores dinámicos.
    """
    # Intentar obtener el atributo dinámico
    try:
        attr = get_attr(obj, field)
    except Exception:
        # Si falla, devolvemos representación del objeto
        return format_html("{}", obj)

    # Booleanos: mostrar iconos
    if isinstance(attr, bool):
        if attr:
            return format_html(
                '<span class="badge badge-lg badge-success"><i class="fa-solid fa-check"></i></span>'
            )
        else:
            return format_html(
                '<span class="badge badge-lg badge-error"><i class="fa-solid fa-xmark"></i></span>'
            )

    # Fechas: mostrar en formato dd/mm/yyyy
    if isinstance(attr, datetime):
        return format_html("{}", attr.strftime("%d/%m/%Y"))
    
    # Campo "id": resolver URL de detalle o mostrar id plano
    if field == "id":
        # Se espera que en el contexto exista algo como:
        # context['crud_urls'] = {'view': 'nombre_url_ver', ...}
        crud_urls = context.get('crud_urls', {})
        nombre_url = crud_urls.get('view')
        if nombre_url:
            try:
                url = reverse(nombre_url, args=[obj.id])
                return format_html(
                    '<button onclick="generic_modal.showModal()"class="cursor-pointer link link-primary" hx-get={} hx-target="#generic_modal_content" hx-swap="innerHTML">{}</button>',
                    url, obj.id
                )
            except Exception:
                pass
        return format_html("{}", obj.id)

    # Campo "usuario": avatar con iniciales, nombre, email
    if field == "usuario" and hasattr(obj, 'usuario') and obj.usuario:
        username = getattr(obj.usuario, 'username', '')
        initials = (username[:2].upper()) if username else ""
        email = getattr(obj.usuario, 'email', '')
        return format_html(
            '<div class="flex items-center gap-3">'
                '<div class="">'
                    '<div class="h-8 w-8 p-1 flex justify-center items-center bg-secondary text-secondary-content rounded-full">'
                        '<span class="text-xs">{}</span>'
                    '</div>'
                '</div>'
                '<div class="text-start">'
                    '<div class="font-bold">{}</div>'
                    '<div class="text-sm opacity-50">{}</div>'
                '</div>'
            '</div>',
            initials, username, email
        )

    # Caso Reserva
    if isinstance(obj, Reserva):
        # campo "espacio"
        if field == "espacio" and obj.espacio:
            max_length = 15
            nombre = getattr(obj.espacio, 'nombre', '') or ""
            ubicacion_nombre = getattr(obj.espacio.ubicacion, 'nombre', '') or ""
            if len(nombre) > max_length:
                nombre_display = nombre[:max_length] + "..."
            else:
                nombre_display = nombre
            if len(ubicacion_nombre) > max_length:
                ubicacion_display = ubicacion_nombre[:max_length] + "..."
            else:
                ubicacion_display = ubicacion_nombre
            piso = getattr(obj.espacio, 'piso', '')
            return format_html(
                '<div>'
                    '<div class="font-semibold">{}</div>'
                    '<div class="text-sm opacity-50">{} - Piso {}</div>'
                '</div>',
                nombre_display, ubicacion_display, piso
            )
        # campo "fecha_uso"
        elif field == "fecha_uso" and getattr(obj, 'fecha_uso', None):
            fecha = obj.fecha_uso
            inicio = getattr(obj, 'hora_inicio', None)
            fin = getattr(obj, 'hora_fin', None)
            fecha_str = fecha.strftime("%d/%m/%Y")
            inicio_str = inicio.strftime("%I:%M %p") if inicio else ""
            fin_str = fin.strftime("%I:%M %p") if fin else ""
            return format_html(
                '<div>'
                    '<div class="font-semibold">{}</div>'
                    '<div class="text-sm opacity-50">{} - {}</div>'
                '</div>',
                fecha_str, inicio_str, fin_str
            )
        # campo "aprobado_por"
        elif field == "aprobado_por":
            aprobado = obj.aprobado_por
            username = aprobado.username if aprobado else "-"
            return format_html(
                '<div><div class="font-semibold">{}</div></div>',
                username
            )
        # campo "estado"
        elif field == "estado":
            estado = obj.estado
            # Caso especial "En uso"
            if estado == Reserva.Estado.APROBADA:
                hoy = date.today()
                ahora = datetime.now().time()
                fecha_uso = getattr(obj, 'fecha_uso', None)
                hora_inicio = getattr(obj, 'hora_inicio', None)
                hora_fin = getattr(obj, 'hora_fin', None)
                if fecha_uso == hoy and hora_inicio and hora_fin:
                    if hora_inicio < ahora < hora_fin:
                        return format_html(
                            '<p class="badge p-1 badge-lg badge-success text-base-100">En uso</p>'
                        )
                cls = "success"
            elif estado == Reserva.Estado.PENDIENTE:
                cls = "warning"
            elif estado == Reserva.Estado.RECHAZADA:
                cls = "error"
            else:
                cls = ""
            texto = str(estado).capitalize()
            return format_html(
                '<p class="badge p-1 badge-lg badge-{} text-base-100">{}</p>',
                cls, texto
            )

        elif field == "espacios":
            relacionados = obj.espacios.all()
            if relacionados.exists():
                max_length = 12  # Aumentamos la longitud máxima
                items = "".join(
                    f"<span class='badge badge-sm badge-outline mr-1 mb-1 text-xs whitespace-nowrap overflow-hidden text-ellipsis max-w-24' title='{e.nombre}'>"
                    f"{e.nombre[:max_length]}{'...' if len(e.nombre) > max_length else ''}"
                    f"</span>" 
                    for e in relacionados[:3]  # Máximo 3 elementos
                )
                # Si hay más elementos, mostrar contador
                extra = relacionados.count() - 3
                if extra > 0:
                    items += f"<span class='badge badge-sm badge-ghost'>+{extra}</span>"
                return mark_safe(f"<div class='w-full min-w-0'><div class='flex flex-wrap gap-1 items-center'>{items}</div></div>")
            else:
                return format_html("<div class='w-full'><span class='opacity-50 text-sm'>Sin espacios</span></div>")
        # Caso Espacio
    if isinstance(obj, Espacio):
        if field == "nombre":
            nombre = getattr(obj, 'nombre', '')
            tipo = getattr(obj, 'tipo', '')
            return format_html(
                '<div>'
                    '<div class="font-semibold">{}</div>'
                    '<div class="text-sm opacity-50">{}</div>'
                '</div>',
                nombre, tipo
            )
        elif field == "ubicacion":
            # Según lógica, quizá mostrar nombre de ubicación o piso
            ubic = getattr(obj, 'ubicacion', None)
            if ubic and isinstance(ubic, str):
                # Si ubicacion es un string, usarlo directamente
                texto = ubic
            else:
                # Si ubicacion es un objeto, intentar obtener el nombre
                texto = getattr(ubic, 'nombre', '') if ubic else ""
            return format_html(
                '<div><div class="font-semibold">{}</div></div>',
                texto
            )

    # Caso Usuario
    if isinstance(obj, Usuario):
        if field in ("username", "email"):
            username = getattr(obj, 'username', '')
            initials = (username[:2].upper()) if username else ""
            email = getattr(obj, 'email', '')
            return format_html(
                '<div class="flex items-center gap-3">'
                    '<div class="">'
                        '<div class="h-8 flex items-center justify-center bg-secondary text-secondary-content rounded-full w-8">'
                            '<span class="text-xs">{}</span>'
                        '</div>'
                    '</div>'
                    '<div class="text-start">'
                        '<div class="font-bold">{}</div>'
                        '<div class="text-sm opacity-50">{}</div>'
                    '</div>'
                '</div>',
                initials, username, email
            )
        elif field == "ubicacion":
            ubic = getattr(obj, 'ubicacion', None)
            texto = getattr(ubic, 'nombre', '-') if ubic else "-"
            return format_html(
                '<div><div class="font-semibold">{}</div></div>',
                texto
            )
        elif field == "group":
            grupo = getattr(obj, 'group', '')
            label = str(grupo).capitalize()
            # Decide clase
            if grupo == Usuario.GRUPOS.MODERADOR:
                clase = "success"
            elif grupo == settings.GRUPOS.USUARIO:
                clase = "warning"
            else:
                clase = "error"
            return format_html(
                '<div><div class="badge badge-lg badge-{} text-base-100 min-w-24">{}</div></div>',
                clase, label
            )

    # Por defecto, mostrar el valor escapado
    if attr is None:
        return format_html("{}", obj)
    return format_html("{}", attr)


# Funciones auxiliares existentes:
def articulo(modelo):
    femeninos = ["reserva", "información", "actividad"]
    return "la" if modelo in femeninos else "el"

def estado_verb(estado):
    estado = estado.lower()
    if estado == "aprobada":
        return "aprobó"
    elif estado == "rechazada":
        return "rechazó"
    elif estado == "pendiente":
        return "marcó como pendiente"
    return f"cambió el estado a {estado}"

@register.simple_tag()
def get_message(logEntry):
    """
    Devuelve un dict con keys: label, description, icon_class, bg_class, text_class, timestamp, full_message (opcional).
    """
    # Actor
    actor_name = logEntry.actor.username if logEntry.actor else None
    actor_display = f'"{actor_name}"' if actor_name else "Alguien"

    # Modelo en minúsculas
    model = logEntry.content_type.model.lower()
    obj_repr = logEntry.object_repr  # texto genérico
    action = logEntry.action
    timestamp = logEntry.timestamp  # datetime
    # Para descripción más rica, intentamos obtener la instancia real
    instance = None
    try:
        model_class = logEntry.content_type.model_class()
        # Usar object_pk; puede ser string, convertir si es necesario
        instance = model_class.objects.filter(pk=logEntry.object_pk).first()
    except Exception:
        instance = None

    # Inicializamos el dict de resultado
    result = {
        "label": "",
        "description": "",
        "icon_class": "",
        "bg_class": "",
        "text_class": "",
        "timestamp": timestamp,
        "full_message": "",  # opcional, si necesitas el texto completo
    }

    # Helper para calcular "time since" en plantilla: usamos timestamp en result
    # Decide según acción y modelo
    # Ejemplos basados en convenciones:
    if action == 0:  # CREATE
        # CREAR
        if model == "reserva":
            result["label"] = "Nueva reserva"
            result["icon_class"] = "fa-plus"
            result["bg_class"] = "info"
            result["text_class"] = "info-content"
            # Description: intentar espacio y usuario
            if instance:
                espacio = getattr(instance, "espacio", None)
                usuario = getattr(instance, "usuario", None)
                nombre_esp = getattr(espacio, "nombre", "") if espacio else ""
                nombre_usr = getattr(usuario, "username", "") if usuario else ""
                if nombre_esp or nombre_usr:
                    result["description"] = f"{nombre_esp} - {nombre_usr}"
                else:
                    result["description"] = obj_repr
            else:
                result["description"] = obj_repr
            result["full_message"] = f"{actor_display} creó reserva \"{obj_repr}\""
        elif model == "usuario":
            result["label"] = "Usuario creado"
            result["icon_class"] = "fa-user-plus"
            result["bg_class"] = "warning"
            result["text_class"] = "warning-content"
            if instance:
                username = getattr(instance, "username", "")
                grupo = getattr(instance, "group", "")
                desc = username
                if grupo:
                    desc += f" - {grupo}"
                result["description"] = desc
            else:
                result["description"] = obj_repr
            result["full_message"] = f"{actor_display} creó usuario \"{obj_repr}\""
        else:
            # Otros modelos: genérico
            result["label"] = f"Nueva {model}" if model in ["reserva", "actividad"] else f"Nuevo {model}"
            result["icon_class"] = "fa-plus"
            result["bg_class"] = "info"
            result["text_class"] = "info-content"
            result["description"] = obj_repr
            result["full_message"] = f"{actor_display} creó {articulo(model)} {model} \"{obj_repr}\""

    elif action == 1:  # UPDATE
        if model == "reserva" and hasattr(logEntry, "changes_dict") and "estado" in getattr(logEntry, "changes_dict", {}):
            nuevo_estado = logEntry.changes_dict["estado"][1]
            # Si cambia a aprobada o rechazada
            if nuevo_estado.lower() == "aprobada":
                result["label"] = "Reserva aprobada"
                result["icon_class"] = "fa-check"
                result["bg_class"] = "success"
                result["text_class"] = "success-content"
            elif nuevo_estado.lower() == "rechazada":
                result["label"] = "Reserva rechazada"
                result["icon_class"] = "fa-times"
                result["bg_class"] = "error"
                result["text_class"] = "error-content"
            else:
                result["label"] = f"Cambio de estado"
                result["icon_class"] = "fa-exchange-alt"
                result["bg_class"] = "warning"
                result["text_class"] = "warning-content"
            # Description: similar a antes
            if instance:
                espacio = getattr(instance, "espacio", None)
                usuario = getattr(instance, "usuario", None)
                nombre_esp = getattr(espacio, "nombre", "") if espacio else ""
                nombre_usr = getattr(usuario, "username", "") if usuario else ""
                if nombre_esp or nombre_usr:
                    result["description"] = f"{nombre_esp} - {nombre_usr}"
                else:
                    result["description"] = obj_repr
            else:
                result["description"] = obj_repr
            result["full_message"] = f"{actor_display} {estado_verb(nuevo_estado)} la reserva \"{obj_repr}\""

        elif model == "espacio" and hasattr(logEntry, "changes_dict") and "disponible" in getattr(logEntry, "changes_dict", {}):
            nuevo_disponible = logEntry.changes_dict["disponible"][1]
            if nuevo_disponible:
                result["label"] = "Espacio disponible"
                result["icon_class"] = "fa-check"
                result["bg_class"] = "success"
                result["text_class"] = "success-content"
                result["description"] = obj_repr
            else:
                result["label"] = "Espacio no disponible"
                result["icon_class"] = "fa-times"
                result["bg_class"] = "error"
                result["text_class"] = "error-content"
                result["description"] = obj_repr
            result["full_message"] = f"{actor_display} {estado_verb(nuevo_disponible)} el espacio \"{obj_repr}\""
            
        else:
            # UPDATE genérico
            if model == "reserva":
                result["label"] = "Reserva actualizada"
                result["icon_class"] = "fa-edit"
                result["bg_class"] = "info"
                result["text_class"] = "info-content"
                if instance:
                    espacio = getattr(instance, "espacio", None)
                    usuario = getattr(instance, "usuario", None)
                    nombre_esp = getattr(espacio, "nombre", "") if espacio else ""
                    nombre_usr = getattr(usuario, "username", "") if usuario else ""
                    result["description"] = f"{nombre_esp} - {nombre_usr}" if (nombre_esp or nombre_usr) else obj_repr
                else:
                    result["description"] = obj_repr
            elif model == "usuario":
                result["label"] = "Usuario actualizado"
                result["icon_class"] = "fa-edit"
                result["bg_class"] = "info"
                result["text_class"] = "info-content"
                if instance:
                    username = getattr(instance, "username", "")
                    result["description"] = username
                else:
                    result["description"] = obj_repr
            else:
                result["label"] = f"{model.capitalize()} actualizado"
                result["icon_class"] = "fa-edit"
                result["bg_class"] = "info"
                result["text_class"] = "info-content"
                result["description"] = obj_repr
            result["full_message"] = f"{actor_display} actualizó la información de {articulo(model)} {model} \"{obj_repr}\""

    elif action == 2:  # DELETE
        if model == "reserva":
            result["label"] = "Reserva eliminada"
            result["icon_class"] = "fa-times"
            result["bg_class"] = "error"
            result["text_class"] = "error-content"
            if instance:
                espacio = getattr(instance, "espacio", None)
                usuario = getattr(instance, "usuario", None)
                nombre_esp = getattr(espacio, "nombre", "") if espacio else ""
                nombre_usr = getattr(usuario, "username", "") if usuario else ""
                result["description"] = f"{nombre_esp} - {nombre_usr}" if (nombre_esp or nombre_usr) else obj_repr
            else:
                result["description"] = obj_repr
        elif model == "usuario":
            result["label"] = "Usuario eliminado"
            result["icon_class"] = "fa-user-times"
            result["bg_class"] = "error"
            result["text_class"] = "error-content"
            if instance:
                username = getattr(instance, "username", "")
                result["description"] = username
            else:
                result["description"] = obj_repr
        else:
            result["label"] = f"{model.capitalize()} eliminado"
            result["icon_class"] = "fa-times"
            result["bg_class"] = "error"
            result["text_class"] = "error-content"
            result["description"] = obj_repr
        result["full_message"] = f"{actor_display} eliminó {articulo(model)} {model} \"{obj_repr}\""

    else:
        # Acción desconocida
        result["label"] = f"Acción en {model}"
        result["icon_class"] = "fa-question"
        result["bg_class"] = "warning"
        result["text_class"] = "warning-content"
        result["description"] = obj_repr
        result["full_message"] = f"{actor_display} realizó una acción desconocida sobre {model} \"{obj_repr}\""

    return result

@register.filter 
def get_color_reserva(reserva: Reserva):
    if reserva.estado == 'pendiente':
        return 'warning'
    elif reserva.estado == 'aprobada':
        return 'success'
    elif reserva.estado == 'rechazada':
        return 'error'
    else:
        return 'info'

@register.filter
def get_field_label(form, field_name):
    """
    Obtiene la etiqueta de un campo del formulario.
    """
    try:
        return form[field_name].label
    except (KeyError, AttributeError):
        return field_name.replace('_', ' ').title()
