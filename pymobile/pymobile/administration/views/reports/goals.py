# -*- coding: utf-8 -*-

from django.http import HttpResponse 
import pymobile.administration.utils as u
import pymobile.administration.models as models
import pymobile.administration.tables as tables
import pymobile.administration.forms as forms

from django.shortcuts import render_to_response, HttpResponseRedirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages

from datetime import date, timedelta
import logging

# Get an instance of a logger
logger = logging.getLogger("file")

# sistemiamo il locale al locale di default della macchina 
import locale
from django.utils.datetime_safe import datetime
locale.setlocale(locale.LC_ALL, '')

TMP_CANVAS="statistiche/obiettivo_trimestrale.html"
TMP_ADMIN= "statistiche/obiettivo_trimestrale_admin.html"
TMP_TABLE="statistiche/obiettivo_trimestrale_table_snippet.html"
TMP_FORM="statistiche/obiettivo_trimestrale_modelform.html"
TMP_DEL="statistiche/obiettivo_trimestrale_deleteform.html"

def get_daily_points(obiettivi, contratti, date):
    out = {}
    
    for obiettivo in obiettivi:
        punteggio_day = 0
        
        contratti_day = contratti.filter(data_inviato=date)
        n = 0
        for contratto in contratti_day:
            # determiniamo il piano tariffario
            pts = models.PianoTariffario.objects.filter(contratto=contratto).iterator()
            
            punteggio_contratto = 0
            for pt in pts:
                q = pt.num
                tariffa = pt.tariffa      
                
                if check_tariffa(obiettivo, tariffa):
                    punteggio_contratto = +q
            
            n += 1
            punteggio_day += punteggio_contratto
        
        out[obiettivo.denominazione] = {"punteggio": punteggio_day,
                                        "contratti": n,} 
    return out         

def get_points(obiettivi, contratti):
    totals = {}
    for obiettivo in obiettivi:
        totals[obiettivo.denominazione] = {"contratti": 0,
                                           "punteggio": 0,
                                           "goal": obiettivo.punteggio,
                                           "msg": ""}
    d = {}
    if contratti.exists():        
        dates = contratti.values("data_inviato").distinct()

        for date in dates:
            data_inviato = date["data_inviato"].strftime("%d/%m/%Y")
            d[data_inviato] = {}
            
            daily_points = get_daily_points(obiettivi, 
                                            contratti, 
                                            date["data_inviato"])
            for denominazione in daily_points.keys():
                d[data_inviato][denominazione] = {"data": data_inviato,
                                                  "punteggio": daily_points[denominazione]["punteggio"],
                                                  "contratti": daily_points[denominazione]["contratti"],}
                totals[denominazione]["punteggio"] += daily_points[denominazione]["punteggio"]
                totals[denominazione]["contratti"] += daily_points[denominazione]["contratti"]
                totals[denominazione]["goal"] -= daily_points[denominazione]["punteggio"]
    
    for denominazione in totals.keys():
        diff = totals[denominazione]["goal"]
        if diff < 0:
            totals[denominazione]["msg"] = "Obiettivo raggiunto (+{})".format(diff)
        elif diff == 0:
            totals[denominazione]["msg"] = "Obiettivo raggiunto"
        else:
            totals[denominazione]["msg"] = "Per raggiungere l'obiettivo mancano {} punti".format(diff)    

    return (d, totals)
    

@login_required
#@user_passes_test(lambda user: not u.is_telefonista(user),)
@user_passes_test(lambda user: u.get_group(user) != "telefonista")
def canvas_obiettivo_trimestrale(request):
    template = TMP_CANVAS
    
    # FIXME: ragionare sulla gestione del periodo
    if request.method == "GET" and request.GET.has_key("fanno") and request.GET.has_key("fquarto"):
        period = u.get_quarter(request.GET)
    else:
        period = u.get_current_quarter()
    
    # in conteggio per il raggiungimento degli obiettivi è fatto sui contratti
    # inviati nel quarto di riferimento
    contratti_inviati = models.Contratto.objects.filter(data_inviato__gte=period[0], 
                                                        data_inviato__lte=period[1], 
                                                        inviato=True)\
                                                .order_by("data_inviato")\
                                                .select_related("piano_tariffario")
    
    # ricaviamo contratti solo degli agenti/telefonisti selezionati 
    if request.method == "GET" and request.GET.has_key("fagente"):
        agenti_ids = u.get_agenti_ids(request.GET)
        if agenti_ids:
            contratti_inviati = contratti_inviati.filter(agente__in=agenti_ids) 
    if request.method == "GET" and request.GET.has_key("ftelefonista"):
        tel_ids = u.get_telefonisti_ids(request.GET)
        if tel_ids:
            contratti_inviati = contratti_inviati.filter(telefonista__in=tel_ids)    
    
    obiettivi = models.Obiettivo.objects.filter(data_inizio__lte=period[0])
    
    d, totals = get_points(obiettivi, contratti_inviati)

#    totals = {}
#    for obiettivo in obiettivi:
#        totals[obiettivo.denominazione] = {"inviati": 0, 
#                                           "caricati": 0,
#                                           "punteggio": 0,}
#    d = {}
#    if contratti_inviati.exists():        
#        dates = contratti_inviati.values("data_inviato").distinct()
#
#        for date in dates:
#            data_inviato = date["data_inviato"].strftime("%d/%m/%Y")
#            d[data_inviato] = {}
#            
#            daily_points = get_daily_points(obiettivi, 
#                                            contratti_inviati, 
#                                            date["data_inviato"])
#            for denominazione in daily_points.keys():
#                d[data_inviato][denominazione] = {"data": data_inviato,
#                                                  "punteggio": daily_points[denominazione]["punteggio"],
#                                                  "inviati": daily_points[denominazione]["contratti"],}
#                totals[denominazione]["punteggio"] += daily_points[denominazione]["punteggio"]
#                totals[denominazione]["inviati"] += daily_points[denominazione]["contratti"]
#            for obiettivo in obiettivi:
#                punteggio_day = 0
#                
#                contratti_day = contratti_inviati.filter(data_inviato=date["data_inviato"])
#                n_inviati = 0
#                for contratto in contratti_day:
#                    # determiniamo il piano tariffario
#                    pts = models.PianoTariffario.objects.filter(contratto=contratto).iterator()
#                    
#                    punteggio_contratto = 0
#                    for pt in pts:
#                        q = pt.num
#                        tariffa = pt.tariffa      
#                        
#                        if check_tariffa(obiettivo, tariffa):
#                            punteggio_contratto = +q
#                    
#                    n_inviati += 1
#                    punteggio_day += punteggio_contratto
#                
#                d[data_inviato][obiettivo.denominazione] = {"data": data_inviato,
#                                                            "punteggio": punteggio_day,
#                                                            "inviati": n_inviati,}    
#                totals[obiettivo.denominazione]["punteggio"] += punteggio_day
#                totals[obiettivo.denominazione]["inviati"] += n_inviati
    
    rows = []        
    date_cur = period[0]
    today = datetime.today().date()
    y_cur = 0
    m_cur = 0
    
    while date_cur <= period[1]:
        if date_cur.year != y_cur:
            year = date_cur.year
            y_cur = date_cur.year
        else:
            year = None
        
        if date_cur.month != m_cur:
            m_cur = date_cur.month
            if date_cur == today:
                month = (date_cur.strftime("%B"), today)
            else:
                month = (date_cur.strftime("%B"), None)
        else:
            if date_cur == today:
                month = (None, today)
            else:    
                month = (None, None)
        
        row = {"anno": year, "mese": month}
        k = date_cur.strftime("%d/%m/%Y")
        if k in d:
            for obiettivo in obiettivi:
                row[obiettivo.denominazione] = d[k][obiettivo.denominazione]
        rows.append(row)
        date_cur += timedelta(1)
    
#    for obiettivo in obiettivi:
#        diff = obiettivo.punteggio - totals[obiettivo.denominazione]["punteggio"]
#        diff = totals[obiettivo.denominazione]["goal"]
#        if diff < 0:
#            totals[obiettivo.denominazione]["msg"] = "Obiettivo raggiunto (+{})".format(diff)
#        elif diff == 0:
#            totals[obiettivo.denominazione]["msg"] = "Obiettivo raggiunto"
#        else:
#            totals[obiettivo.denominazione]["msg"] = "Per raggiungere l'obiettivo mancano {} punti".format(diff)    
            
    if request.is_ajax():
        data = {"rows": rows, "obiettivi": obiettivi, "period": period, "totali": totals}
        return render_to_response(template,
                                  data,
                                  context_instance=RequestContext(request))        
    
    filterform = forms.ObiettivoFilterForm()
    data = {"rows": rows, "obiettivi": obiettivi, "period": period, 
            "totali": totals, "filterform": filterform,}
    return render_to_response(template,
                              data,
                              context_instance=RequestContext(request))
                
def check_tariffa(obiettivo, tariffa):
    parametri = obiettivo.parametri
    values = u.values_from_parametri(parametri)
    result = True
    if values:
        for k, v in values.iteritems():
            if k == "gestore":
                if tariffa.gestore != v:
                    result = False
                    break
            if k == "profilo":
                if tariffa.profilo != v:
                    result = False
                    break
            if k == "tipo":
                if tariffa.tipo != v:
                    result = False
                    break
            if k == "fascia":
                if tariffa.fascia != v:
                    result = False
                    break
            if k == "servizio":
                if tariffa.servizio != v:
                    result = False
                    break
        
    return result

@login_required
#@user_passes_test(lambda user: not u.is_telefonista(user),)
@user_passes_test(lambda user: u.get_group(user) != "telefonista")
def init_obiettivo_trimestrale(request):
    template = TMP_ADMIN
    # determiniamo solo gli obiettivi attivi
    objs = models.Obiettivo.objects.filter(data_fine__isnull=True)
    initial = {}
    pag = 1
    ordering = None
    
    if request.method == "GET" and request.GET:
        query_get = request.GET.copy()
        initial = {}
        
        if query_get.has_key("pag"):
            pag = query_get["pag"]
            del query_get["pag"]
        if query_get.has_key("sort"):
            ordering = query_get["sort"]
            del query_get["sort"]
        if query_get:
            objs, initial = u.filter_objs(objs, query_get)
        
    table = tables.ObiettivoTable(objs, order_by=(ordering,))
    table.paginate(page=pag)
    
    if request.is_ajax():
        template = table.as_html()
        return HttpResponse(template)
        
    data = {"modeltable": table,}
    return render_to_response(template, data,
                              context_instance=RequestContext(request))

@login_required
#@user_passes_test(lambda user: not u.is_telefonista(user),)
@user_passes_test(lambda user: u.get_group(user) != "telefonista")
def add_obiettivo_trimestrale(request):  
    template = TMP_FORM
    action = "add"
    
    if request.method == "POST":
        post_query = request.POST.copy()
        form = forms.ObiettivoForm(post_query)
        
        if form.is_valid():
            new_obj = form.save()
            
            logger.debug("{}: aggiunto l'obiettivo trimestrale {} [id={}]"
                         .format(request.user, new_obj, new_obj.id))
            messages.add_message(request, messages.SUCCESS, 'Obiettivo trimestrale aggiunto')
            if request.POST.has_key("add_another"):              
                return HttpResponseRedirect(reverse("add_obiettivo_trimestrale")) 
            else:
                return HttpResponseRedirect(reverse("init_obiettivo_trimestrale"))
    else:
        form = forms.ObiettivoForm()    
        
    data = {"modelform": form, "action": action,}                
    return render_to_response(template, 
                              data,
                              context_instance=RequestContext(request))

@login_required
#@user_passes_test(lambda user: not u.is_telefonista(user),)
@user_passes_test(lambda user: u.get_group(user) != "telefonista")
def mod_obiettivo_trimestrale(request, object_id):
    template = TMP_FORM
    action = "mod"
    
    if request.method == "POST":
        post_query = request.POST.copy()
        obj = get_object_or_404(models.Obiettivo, pk=object_id)
        form = forms.ObiettivoForm(post_query, instance=obj)
    
        if form.is_valid():
            new_obj = form.save()
            
            logger.debug("{}: modificato l'obiettivo trimestrale {} [id={}]"
                         .format(request.user, new_obj, new_obj.id))
            messages.add_message(request, messages.SUCCESS, 'Obiettivo trimestrale modificato')
            if request.POST.has_key("add_another"):              
                return HttpResponseRedirect(reverse("add_obiettivo_trimestrale")) 
            else:
                return HttpResponseRedirect(reverse("init_obiettivo_trimestrale", 
                                                    args=[object_id]))
    else:
        obj = get_object_or_404(models.Obiettivo, pk=object_id) 
        form = forms.ObiettivoForm(instance=obj)
    
    data = {"modelform": form, "action": action, "obiettivo": obj,}
    return render_to_response(template,
                              data,
                              context_instance=RequestContext(request))

@login_required
#@user_passes_test(lambda user: not u.is_telefonista(user),)
@user_passes_test(lambda user: u.get_group(user) != "telefonista")
def del_obiettivo_trimestrale(request):
    template = TMP_DEL
    
    if request.method == "POST":
        query_post = request.POST.copy()
        
        if query_post.has_key("id"):
            # cancelliamo
            ids = query_post.getlist("id")
            models.Obiettivo.objects.filter(id__in=ids).delete()
            url = reverse("init_obiettivo_trimestrale")
            
            if len(ids) == 1:
                logger.debug("{}: eliminato l'obiettivo trimestrale [id={}]"
                             .format(request.user, ids))
                messages.add_message(request, messages.SUCCESS, 'Obiettivo trimestrale eliminato')
            elif len(ids) > 1:
                logger.debug("{}: eliminati gli obiettivi trimestrali [id={}]"
                             .format(request.user, ids))
                messages.add_message(request, messages.SUCCESS, 'Obiettivi trimestrali eliminati')
            return HttpResponse('''
                <script type='text/javascript'>
                    opener.redirectAfter(window, '{}');
                </script>'''.format(url))
    
    query_get = request.GET.copy()
    ids = query_get.getlist("id")      
    objs = models.Obiettivo.objects.filter(id__in=ids)
    
    logger.debug("{}: ha intenzione di eliminare gli obiettivi trimestrali {}"
                 .format(request.user, [(str(obj), "id=" + str(obj.id)) for obj in objs]))
    
    data = {"objs": objs}
    return render_to_response(template,
                              data,
                              context_instance=RequestContext(request))
