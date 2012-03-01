# -*- coding: utf-8 -*-

from django.http import HttpResponse          
from django.shortcuts import render_to_response, HttpResponseRedirect, get_object_or_404
from django.template import RequestContext
#from django.template.loader import render_to_string
from django.db.models import Q
#from django.utils import simplejson
from django.core.urlresolvers import reverse
from django.forms.models import inlineformset_factory
#from django.db.models.loading import get_model
#from django.views.generic.simple import redirect_to
#from django.forms.models import inlineformset_factory

import operator
import pymobile.administration.models as models
import pymobile.administration.forms as forms
import pymobile.administration.tables as tables
import pymobile.administration.utils as u

# Create your views here.

TMP_ADMIN="contratto/admin.html"
TMP_FORM="contratto/modelform.html"
TMP_DEL="contratto/deleteform.html"
TMP_VIEW="contratto/view.html"

def init(request):
    template = TMP_ADMIN
    objs = models.Contratto.objects.all()
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
        
    table = tables.ContrattoTable(objs, order_by=(ordering,))
    table.paginate(page=pag)                   

    if request.is_ajax():
        template = table.as_html()
        return HttpResponse(template)
    
    filterform = forms.ContrattoFilterForm(initial=initial)
    
    data = {"modeltable": table, "filterform": filterform}
    return render_to_response(template, data,
                              context_instance=RequestContext(request))

def add_object(request):  
    template = TMP_FORM
    action = "Aggiungi"
    PianoTariffarioFormset = inlineformset_factory(models.Contratto, 
                                                   models.PianoTariffario, 
                                                   forms.PianoTariffarioForm,
                                                   formset = forms.PianoTariffarioInlineFormset,
                                                   can_delete=False,
                                                   extra=1,)
        
    if request.method == "POST":
        post_query = request.POST.copy()
        print(request.FILES)
        form = forms.ContrattoForm(post_query, request.FILES)
        
        if form.is_valid():
            contratto = form.save(commit=False)
            formset = PianoTariffarioFormset(post_query, instance=contratto)
            
            if formset.is_valid():
                form.save()
                formset.save()
            
                if request.POST.has_key("add_another"):              
                    return HttpResponseRedirect(reverse("add_contratto")) 
                else:
                    url = reverse("init_contratto")
                    return HttpResponse('''
                                    <script type='text/javascript'>
                                        opener.redirectAfter(window, '{}');
                                    </script>'''.format(url)) 
        else:
            formset = PianoTariffarioFormset(post_query)
    else:
        form = forms.ContrattoForm()
        formset = PianoTariffarioFormset(instance=models.Contratto())                
    
    data = {"modelform": form, "action": action, "modelformset": formset,}                
    return render_to_response(template, 
                              data,
                              context_instance=RequestContext(request))

def mod_object(request, object_id):
    template = TMP_FORM
    action = "Modifica"
    PianoTariffarioFormset = inlineformset_factory(models.Contratto, 
                                                   models.PianoTariffario, 
                                                   forms.PianoTariffarioForm,
                                                   formset = forms.PianoTariffarioInlineFormset,
                                                   can_delete=True,
                                                   extra=0,)
    
    if request.method == "POST":
        post_query = request.POST.copy()
        
        print(request.FILES)
        
        obj = get_object_or_404(models.Contratto, pk=object_id)
        form = forms.ContrattoForm(post_query, request.FILES, instance=obj)
        
        if form.is_valid():
            contratto = form.save(commit=False)
            formset = PianoTariffarioFormset(post_query, instance=contratto)
            
            if formset.is_valid():
                form.save()
                formset.save() 
            
                if request.POST.has_key("add_another"):              
                    return HttpResponseRedirect(reverse("add_contratto")) 
                else:
                    url = reverse("view_contratto", args=[object_id,])
                    return HttpResponse('''
                                    <script type='text/javascript'>
                                        opener.redirectAfter(window, '{}');
                                    </script>'''.format(url))   
        else:
            formset = PianoTariffarioFormset(post_query, instance=obj)
    else:
        contratto = get_object_or_404(models.Contratto, pk=object_id)
        form = forms.ContrattoForm(instance=contratto)
        formset = PianoTariffarioFormset(instance=contratto)        
    
    data = {"modelform": form, "action": action, "modelformset": formset,} 
    return render_to_response(template,
                              data,
                              context_instance=RequestContext(request))

def del_object(request):
    template = TMP_DEL
    
    if request.method == "POST":
        query_post = request.POST.copy()
        
        if query_post.has_key("id"):
            # cancelliamo
            ids = query_post.getlist("id")
            models.Contratto.objects.filter(id__in=ids).delete()
            
            url = reverse("init_contratto")
            return HttpResponse('''
                <script type='text/javascript'>
                    opener.redirectAfter(window, '{}');
                </script>'''.format(url))
    
    query_get = request.GET.copy()
    ids = query_get.getlist("id")      
    objs = models.Contratto.objects.filter(id__in=ids)
    
    data = {"objs": objs}
    return render_to_response(template,
                              data,
                              context_instance=RequestContext(request))


def add_child_object(request, field_name):
    action = "Aggiungi" 
    
    def get_child_form(field_name):  
        f = field_name.capitalize() + "Form"
        if field_name == "cliente":
            t = "contratto/cliente_modelform.html"
        elif field_name == "agente":
            t = "contratto/agente_modelform.html"
        elif field_name == "tariffa":
            t = "contratto/tariffa_modelform.html"        
        return getattr(forms, f), t  
    
    if request.method == "POST":
        post_query = request.POST.copy()
        form_class, template = get_child_form(field_name)
        form = form_class(post_query)
        
        if form.is_valid():
            try:
                new_obj = form.save()
            except form.ValidationError:
                new_obj = None
                                
            if new_obj: 
                return HttpResponse('''
                    <script type="text/javascript">
                        opener.closeSubModelform(window, "{}", "{}");
                    </script>'''.format(new_obj.pk, new_obj))
    else:
        form_class, template = get_child_form(field_name)
        form = form_class()
      
    data = {"modelform": form, "action": action,}     
    return render_to_response(template, 
                              data,
                              context_instance=RequestContext(request))