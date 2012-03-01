# -*- coding: utf-8 -*-

#import operator
#from django.http import HttpResponse 
import pymobile.administration.utils as u
import pymobile.administration.models as models
import pymobile.administration.tables as tables
import pymobile.administration.forms as forms
from django.shortcuts import render_to_response
#from django.db.models import Sum
from django.template import RequestContext
#from datetime import datetime
#from django.db.models import Q

def inout(request):
    template = "statistiche/entrate_uscite.html"
    
    if request.method == "GET" and request.GET.has_key("fperiodo"):
        period = u.get_period(request.GET)
    else:
        period = u.get_current_month()
        
    # entrate
    # 1 - contratti stipulati
    contratti = models.Contratto.objects.filter(data_stipula__gte=period[0], 
                                                data_stipula__lte=period[1])\
                                                .order_by("data_stipula")\
                                                .select_related("piano_tariffario")
                                                
    
    # ricaviamo contratti solo degli agenti selezionati 
    if request.method == "GET" and request.GET.has_key("fagente"):
        agenti_ids = u.get_agenti_ids(request.GET)
    
        if agenti_ids:
            contratti = contratti.filter(agente__in=agenti_ids) 
    if request.method == "GET" and request.GET.has_key("ftelefonista"):
        tel_ids = u.get_telefonisti_ids(request.GET)
        if tel_ids:
            contratti = contratti.filter(telefonista__in=tel_ids)    
    
    objs_in = []
    objs_out = []
    
    if contratti.exists():
        dates = contratti.values("data_stipula").distinct()
        for date in dates:
            in_tot_day = 0
            out_tot_day = 0
            out_tot_prov_agt_day = 0
            out_tot_prov_tel_day = 0
            out_tot_prov_bonus_agt_day = 0
            out_tot_prov_bonus_tel_day = 0 
            print(date)
            contratti_day = contratti.filter(data_stipula=date["data_stipula"]).iterator()
            n = 0
            for contratto in contratti_day:
                # informazioni utili
                cliente = contratto.cliente
                agente = contratto.agente
                telefonista = None
                if contratto.appuntamento:
                    telefonista = contratto.appuntamento.telefonista
                
                # uscite: bonus per agente/telefonista in base al contratto
                vas_agente = contratto.vas_agente
                vas_telefonista = contratto.vas_telefonista
                
                # determiniamo il piano tariffario
                pts = models.PianoTariffario.objects.filter(contratto=contratto).iterator()
                print(pts)
#                pts = contratto.piano_tariffario.iterator()
                in_tot_contratto = 0
                out_tot_prov_agt_contratto = 0
                out_tot_prov_tel_contratto = 0
                out_tot_prov_bonus_agt_contratto = 0
                out_tot_prov_bonus_tel_contratto = 0
                for pt in pts:
                    tariffa = pt.tariffa
                    q = pt.num
                    sac = tariffa.sac
                    print(tariffa, q, sac)
                    
                    # determiniamo le entrate dovute alla tariffa del contratto considerato
                    in_tot_contratto += sac * q
                    
                    # determiniamo le uscite dovute alla tariffa del contratto considerato
                    # 1: provvigione dovuta all'agente:
                    prov_agente = calc_provvigione(agente, cliente, tariffa, date["data_stipula"])
                    out_tot_prov_agt_contratto += prov_agente[0] * q
                    out_tot_prov_bonus_agt_contratto += prov_agente[1] * q
                    # 2: provvigione dovuta al telefonista
                    prov_telefonista = calc_provvigione(telefonista, cliente, tariffa, date["data_stipula"])
                    out_tot_prov_tel_contratto += prov_telefonista[0] * q
                    out_tot_prov_bonus_tel_contratto += prov_telefonista[1] * q
                    
                # determiniamo le entrate della giornata
                in_tot_day += in_tot_contratto
                
                # determiniamo le uscite della giornata
                out_tot_prov_agt_day += out_tot_prov_agt_contratto
                out_tot_prov_bonus_agt_day += out_tot_prov_bonus_agt_contratto
                out_tot_prov_tel_day += out_tot_prov_tel_contratto
                out_tot_prov_bonus_tel_day += out_tot_prov_bonus_tel_contratto
                out_tot_day = out_tot_prov_agt_day + out_tot_prov_bonus_agt_day + \
                    out_tot_prov_tel_day + out_tot_prov_bonus_tel_day + \
                    vas_telefonista + vas_agente
                
                n += 1
                
            # inseriamo i dati per la tabella delle entrate
            obj_in = {"data": date["data_stipula"], "n_stipulati": n, "entrate": in_tot_day}
            obj_out = {"data": date["data_stipula"], "n_stipulati": n, "uscite": out_tot_day,
                       "prov_agt": out_tot_prov_agt_day, 
                       "prov_bonus_agt": out_tot_prov_bonus_agt_day,
                       "prov_tel": out_tot_prov_tel_day,
                       "prov_bonus_tel": out_tot_prov_bonus_tel_day,}
            objs_in.append(obj_in)
            objs_out.append(obj_out)
    
    # creiamo le tabelle 
    table_in = tables.InTable(objs_in, prefix="in")
    table_in.paginate(page=request.GET.get("in-page", 1))
    table_in.order_by = request.GET.get("in-sort")
    table_out = tables.OutTable(objs_out, prefix="out")
    table_out.paginate(page=request.GET.get("out-page", 1))
    table_out.order_by = request.GET.get("out-sort")
    
    if request.is_ajax():
        data = {"table_in": table_in,
                "table_out": table_out,
                "period": (period[0], period[1])}
        return render_to_response("statistiche/inouttable_snippet.html", data,
                                  context_instance=RequestContext(request))   
    
    filterform = forms.InOutFilterForm()
    
    data = {"table_in": table_in,
            "table_out": table_out,
            "filterform": filterform,
            "period": (period[0], period[1])}
    return render_to_response(template, data,
                              context_instance=RequestContext(request))  

def calc_provvigione(dipendente, cliente, tariffa, date):
    # determiniamo la modalità di calcolo della retribuzione per il dipendente
    # prima verifichiamo se vi una variazione della retribuzione, altrimenti usiamo
    # la retribuzione standard corrente
    retribuzione = models.RetribuzioneDipendente.objects.get(variazione=True, 
                                                             data_inizio__lte=date,
                                                             data_fine__gte=date)
    if not retribuzione.exists():
        retribuzione = models.RetribuzioneDipendente.objects.filter(variazione=False,
                                                                    data_inizio__lte=date)\
                                                                    .order_by("-data_inizio")[0]
                                                                    
    provvigione_contratto = retribuzione.provvigione_contratto
    provvigione_bonus = retribuzione.provvigione_bonus
    
    # calcoliamo la provvigione per il contratto, intesa come singola tariffa
    ret_contratto = 0
    if dipendente.tipo == "agt":
        # provvigione contratto è un valore percentuale
        ret_contratto = tariffa.sac * provvigione_contratto / 100
    elif dipendente.tipo == "tel":
        ret_contratto = provvigione_contratto
    
    # calcoliamo la provvigione bonus (se presente)
    ret_bonus = 0
    if provvigione_bonus:
        values = u.values_from_provvigione_bonus(provvigione_bonus)
        
        for value in values:
            res = False
            pars = value["parameters"]
            for k, v in pars.iteritems():
                if k == "blindato":
                    if cliente.blindato != v:
                        res = False
                        break
                    else:
                        res = True
                elif k == "gestore":
                    if tariffa.gestore != v:
                        res = False
                        break
                    else:
                        res = True
                elif k == "profilo":
                    if tariffa.profilo != v:
                        res = False
                        break
                    else:
                        res = True
                elif k == "tipo":
                    if tariffa.tipo != v:
                        res = False
                        break
                    else:
                        res = True
                elif k == "fascia":
                    if tariffa.fascia != v:
                        res = False
                        break
                    else:
                        res = True
                elif k == "servizio":
                    if tariffa.servizio != v:
                        res = False
                        break
                    else:
                        res = True
            
            if res:
                ret_bonus += value["provvigione"]
        
    return (ret_contratto, ret_bonus)